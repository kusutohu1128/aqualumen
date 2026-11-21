package dev.aqualumen.physics;

import java.util.*;

/** Pure read-only voxel-boundary model; no Minecraft or OpenGL dependency. */
public final class BathymetryField {
    public static final int SIZE=64, MAX_WATER_CELLS=32;
    public static final double SURFACE_TOLERANCE=0.12;
    private record Cached(Column value,int tick) {}
    private final Map<Long,Cached> cache=new HashMap<>();
    private static final int[] ORDER=order();
    private Object worldIdentity;
    private int originX,originZ,cursor,tick;
    private double referenceSurface;
    private static int[] order() {
        Integer[] indexes=new Integer[SIZE*SIZE];
        for(int i=0;i<indexes.length;i++) indexes[i]=i;
        Arrays.sort(indexes,Comparator.comparingInt(i->(i%SIZE-32)*(i%SIZE-32)+(i/SIZE-32)*(i/SIZE-32)));
        return Arrays.stream(indexes).mapToInt(Integer::intValue).toArray();
    }
    private static long key(int x,int z) {return ((long)x<<32) ^ (z&0xffffffffL);}
    private int nextIndex() {int i=ORDER[cursor];cursor=(cursor+1)%(SIZE*SIZE);return i;}
    public void reset() {cache.clear();worldIdentity=null;cursor=0;}
    public interface World {
        boolean loaded(int blockX,int blockZ);
        Cell cell(int x,int y,int z);
        int minY();
        int maxY();
    }
    public record Cell(boolean water,float height,boolean fullSolid) {}
    public record Column(float depth,double surface,boolean valid) {
        public static final Column UNKNOWN=new Column(0,0,false);
    }
    public static final class Snapshot {
        public final int originX,originZ,scanned;
        public final double referenceSurface;
        private final Column[] columns;
        private Snapshot(int x,int z,double reference,Column[] values,int scanned) {
            originX=x;originZ=z;referenceSurface=reference;columns=values;this.scanned=scanned;
        }
        public Column columnAt(int worldX,int worldZ) {
            int x=worldX-originX,z=worldZ-originZ;
            return x>=0 && x<SIZE && z>=0 && z<SIZE?columns[z*SIZE+x]:Column.UNKNOWN;
        }
    }
    public Snapshot update(World world,Object identity,int x,int z,double reference,int budget) {
        if(budget<0 || budget>64) throw new IllegalArgumentException("Column budget must be 0..64");
        if(identity!=worldIdentity || Math.abs(x-originX)>16 || Math.abs(z-originZ)>16
                || !Double.isFinite(reference) || Math.abs(reference-referenceSurface)>SURFACE_TOLERANCE) reset();
        worldIdentity=identity;originX=x;originZ=z;referenceSurface=reference;tick++;
        // Only retain this bounded world-anchored window. A one-cell camera move does not rescan all cells.
        cache.entrySet().removeIf(e->{int cx=(int)(e.getKey()>>32),cz=(int)(long)e.getKey();
            return cx<x || cx>=x+SIZE || cz<z || cz>=z+SIZE
                    || (e.getValue().value.valid() && (!world.loaded(cx,cz)
                    || Math.abs(e.getValue().value.surface()-reference)>SURFACE_TOLERANCE));});
        int scanned=0;
        if(Double.isFinite(reference)) {
            // Refresh a fair rolling subset even while newly exposed columns are filling.
            int refresh=Math.min(budget/4,cache.size());
            for(int visited=0;visited<SIZE*SIZE && scanned<refresh;visited++) {
                int i=nextIndex(),cx=x+i%SIZE,cz=z+i/SIZE;
                if(cache.containsKey(key(cx,cz))) {scan(world,cx,cz,reference);scanned++;}
            }
            for(int i:ORDER) {
                if(scanned>=budget) break;
                int cx=x+i%SIZE,cz=z+i/SIZE;
                if(!cache.containsKey(key(cx,cz))) {scan(world,cx,cz,reference);scanned++;}
            }
            for(int visited=0;visited<SIZE*SIZE && scanned<budget;visited++) {
                int i=nextIndex(),cx=x+i%SIZE,cz=z+i/SIZE;
                Cached old=cache.get(key(cx,cz));
                if(old!=null && old.tick()!=tick) {scan(world,cx,cz,reference);scanned++;}
            }
        }
        Column[] values=new Column[SIZE*SIZE];
        for(int i=0;i<values.length;i++) {
            Cached stored=cache.get(key(x+i%SIZE,z+i/SIZE));
            values[i]=stored==null?Column.UNKNOWN:stored.value();
        }
        return new Snapshot(x,z,reference,values,scanned);
    }
    private void scan(World world,int x,int z,double reference) {
        cache.put(key(x,z),new Cached(extract(world,x,z,reference),tick));
    }
    public static Column extract(World world,int x,int z,double referenceSurface) {
        if(!Double.isFinite(referenceSurface) || !world.loaded(x,z)) return Column.UNKNOWN;
        int base=(int)Math.floor(referenceSurface);
        if(base<world.minY() || base>world.maxY()) return Column.UNKNOWN;
        // A matching surface can only lie in one of these cells. Never search an unrelated pool.
        for(int top=base-1;top<=base+1;top++) {
            if(top<world.minY() || top+1>=world.maxY()) continue;
            Cell cell=world.cell(x,top,z);
            if(!cell.water() || cell.fullSolid() || !Float.isFinite(cell.height())
                    || cell.height()<=0 || cell.height()>1) continue;
            double surface=top+cell.height();
            if(Math.abs(surface-referenceSurface)>SURFACE_TOLERANCE
                    || world.cell(x,top+1,z).water()) continue;
            for(int down=1;down<=MAX_WATER_CELLS;down++) {
                int y=top-down;
                if(y<world.minY()) return Column.UNKNOWN;
                Cell below=world.cell(x,y,z);
                if(!below.water()) {
                    if(!below.fullSolid()) return Column.UNKNOWN;
                    float depth=(float)(surface-(y+1));
                    return depth>0 && Float.isFinite(depth)?new Column(depth,surface,true):Column.UNKNOWN;
                }
                // Intrinsic source-fluid height is 8/9 even below another water block.
                // The consecutive water cell above fills that local cell to its top.
                if(below.fullSolid() || !Float.isFinite(below.height())
                        || below.height()<=0 || below.height()>1) return Column.UNKNOWN;
            }
            return Column.UNKNOWN; // Bounded unknown, not an invented deep floor.
        }
        return Column.UNKNOWN;
    }
}
