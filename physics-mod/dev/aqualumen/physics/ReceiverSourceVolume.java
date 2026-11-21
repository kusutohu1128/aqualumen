package dev.aqualumen.physics;

import java.util.Objects;
import java.util.List;
import java.util.ArrayList;

public final class ReceiverSourceVolume {
    public record Surface(ReceiverRadianceVolume.Epoch epoch, String blockId, float[] total, float[] sun) {
        public Surface {
            Objects.requireNonNull(epoch); Objects.requireNonNull(blockId);
            total=total.clone(); sun=sun.clone();
            if(total.length!=4 || sun.length!=4) throw new IllegalArgumentException("Unpaired source channels");
        }
        @Override public float[] total() { return total.clone(); }
        @Override public float[] sun() { return sun.clone(); }
    }
    public interface World extends ReceiverField.World {
        boolean fullWater(int x,int y,int z);
        default float partialWaterHeight(int x,int y,int z) { return 0; }
        default float upperWaterHeight(int x,int y,int z) { return 0; }
        Surface shadeTop(int x,int y,int z);
        default void beginValidation() { }
        default List<ShadedTop> shadeTops(List<Top> tops) {
            var results=new ArrayList<ShadedTop>();
            for(var top:tops) results.add(new ShadedTop(top,shadeTop(top.x(),top.y(),top.z())));
            return List.copyOf(results);
        }
    }
    public record Top(int x,int y,int z) {
        @Override public int hashCode() {
            int hash=x*0x9e3779b9 ^ Integer.rotateLeft(y*0x85ebca6b,11) ^ Integer.rotateLeft(z*0xc2b2ae35,22);
            hash^=hash>>>16;
            hash*=0x85ebca6b;
            hash^=hash>>>13;
            return hash;
        }
    }
    public record ShadedTop(Top top,Surface surface) { }
    private ReceiverSourceVolume() { }

    public static ReceiverRadianceVolume capture(World world, ReceiverField.Bounds bounds, ReceiverRadianceVolume.Epoch epoch) {
        Objects.requireNonNull(world); Objects.requireNonNull(bounds); Objects.requireNonNull(epoch);
        int count=bounds.width()*bounds.height()*bounds.depth();
        float[] cells=new float[count*4], total=new float[count*4], sun=new float[count*4], faces=new float[count*4];
        var identities=new ReceiverField.Cell[count];
        for(int y=0;y<bounds.height();y++) for(int z=0;z<bounds.depth();z++) for(int x=0;x<bounds.width();x++) {
            int wx=bounds.x()+x, wy=bounds.y()+y, wz=bounds.z()+z;
            int pixel=x+bounds.width()*(y*bounds.depth()+z);
            if(!world.loaded(wx,wz) || wy<world.minY() || wy>=world.maxY()) continue;
            var cell=world.receiverCell(wx,wy,wz); identities[pixel]=cell;
            if(cell.kind()==ReceiverField.Kind.WATER && world.fullWater(wx,wy,wz)) cells[pixel*4]=2;
            else if(cell.kind()==ReceiverField.Kind.WATER) {
                float height=world.partialWaterHeight(wx,wy,wz);
                if(Float.isFinite(height) && height>0 && height<2 && height!=1) {
                    cells[pixel*4]=4; cells[pixel*4+1]=height; cells[pixel*4+2]=1; cells[pixel*4+3]=1;
                }
            }
            else if(cell.kind()==ReceiverField.Kind.AIR) {
                float height=world.upperWaterHeight(wx,wy,wz);
                if(Float.isFinite(height) && height>-1 && height<0) {
                    cells[pixel*4]=5; cells[pixel*4+1]=height; cells[pixel*4+2]=1; cells[pixel*4+3]=1;
                }
            }
            if(cell.kind()==ReceiverField.Kind.OPAQUE) cells[pixel*4]=3;
        }
        var tops=new ArrayList<Top>();
        for(int y=0;y<bounds.height();y++) for(int z=0;z<bounds.depth();z++) for(int x=0;x<bounds.width();x++) {
            int pixel=x+bounds.width()*(y*bounds.depth()+z), offset=pixel*4;
            if(cells[offset]!=3) continue;
            int wx=bounds.x()+x, wy=bounds.y()+y, wz=bounds.z()+z;
            if(wy+1>=world.maxY() || !world.fullWater(wx,wy+1,wz)) continue;
            tops.add(new Top(wx,wy,wz));
        }
        var shadedTops=world.shadeTops(List.copyOf(tops));
        if(shadedTops==null || shadedTops.size()!=tops.size()) throw new IllegalStateException("Receiver source batch extent mismatch");
        for(int index=0;index<tops.size();index++) {
            var top=tops.get(index); var item=shadedTops.get(index);
            if(item==null || !top.equals(item.top())) throw new IllegalStateException("Receiver source batch ownership mismatch");
            int pixel=top.x()-bounds.x()+bounds.width()*((top.y()-bounds.y())*bounds.depth()+top.z()-bounds.z());
            int offset=pixel*4;
            var shaded=item.surface();
            if(shaded==null || shaded.epoch().world()!=epoch.world() || shaded.epoch().frame()!=epoch.frame()
                    || shaded.epoch().resources()!=epoch.resources() || !identities[pixel].blockId().equals(shaded.blockId())) continue;
            float[] source=shaded.total(), direct=shaded.sun();
            if(source[3]!=1 || direct[3]!=1) continue;
            System.arraycopy(source,0,total,offset,4); System.arraycopy(direct,0,sun,offset,4);
            faces[offset+1]=1; faces[offset+3]=1;
        }
        world.beginValidation();
        for(int y=0;y<bounds.height();y++) for(int z=0;z<bounds.depth();z++) for(int x=0;x<bounds.width();x++) {
            int wx=bounds.x()+x, wy=bounds.y()+y, wz=bounds.z()+z;
            int pixel=x+bounds.width()*(y*bounds.depth()+z);
            if(identities[pixel]==null) continue;
            if(!world.loaded(wx,wz) || !identities[pixel].equals(world.receiverCell(wx,wy,wz))
                    || cells[pixel*4]==2 && !world.fullWater(wx,wy,wz)
                    || cells[pixel*4]==4 && world.partialWaterHeight(wx,wy,wz)!=cells[pixel*4+1]
                    || cells[pixel*4]==5 && world.upperWaterHeight(wx,wy,wz)!=cells[pixel*4+1]
                    || total[pixel*4+3]==1 && !world.fullWater(wx,wy+1,wz))
                throw new IllegalStateException("Receiver geometry changed during source shading");
        }
        return new ReceiverRadianceVolume(epoch,bounds,cells,total,sun,faces);
    }
}
