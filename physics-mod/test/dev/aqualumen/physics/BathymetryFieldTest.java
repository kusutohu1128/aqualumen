package dev.aqualumen.physics;

public final class BathymetryFieldTest {
    static class Voxels implements BathymetryField.World {
        int reads;
        int floor=59;
        boolean available=true;
        public boolean loaded(int x,int z) {return available;}
        public int minY() {return -64;}
        public int maxY() {return 320;}
        public BathymetryField.Cell cell(int x,int y,int z) {
            reads++;
            if(y>floor&&y<=62) return new BathymetryField.Cell(true,0.8888889f,false);
            return new BathymetryField.Cell(false,0,y<=floor);
        }
    }
    public static void main(String[] args) {
        var column=BathymetryField.extract(new Voxels(),0,0,62.8888889);
        if(!column.valid()||Math.abs(column.depth()-2.8888889)>0.00001)
            throw new AssertionError("Continuous real water column must expose depth to confirmed full-solid floor");
        System.out.println("PASS bathymetry continuous-column public extraction");
        Voxels unavailable=new Voxels();unavailable.available=false;
        if(BathymetryField.extract(unavailable,0,0,62.8888889).valid() || unavailable.reads!=0)
            throw new AssertionError("Unloaded columns must never cross the voxel boundary");
        for(int kind=0;kind<5;kind++) {
            final int mode=kind;
            Voxels uncertain=new Voxels() {
                public BathymetryField.Cell cell(int x,int y,int z) {
                    if(mode==0 && y==59) return new BathymetryField.Cell(false,0,false);
                    if(mode==1 && y==61) return new BathymetryField.Cell(false,0,false);
                    if(mode==2 && y<60) return new BathymetryField.Cell(true,1,false);
                    if(mode==3 && y==62) return new BathymetryField.Cell(true,Float.NaN,false);
                    if(mode==4 && y==61) return new BathymetryField.Cell(true,Float.NaN,false); // waterlogged partial collision
                    return super.cell(x,y,z);
                }
            };
            if(BathymetryField.extract(uncertain,0,0,62.8888889).valid())
                throw new AssertionError("Air/partial floor, broken/deep column and invalid fluid are unknown: "+kind);
        }
        if(BathymetryField.extract(new Voxels(),0,0,64.8888889).valid()
                || BathymetryField.extract(new Voxels(),0,0,Double.NaN).valid())
            throw new AssertionError("Different stacked planes and nonfinite surface must not be invented");
        System.out.println("PASS bathymetry loaded/floor/continuity/depth-cap/plane/finite boundaries");
        BathymetryField field=new BathymetryField();Voxels voxels=new Voxels();Object identity=new Object();
        var snapshot=field.update(voxels,identity,-32,-32,62.8888889,16);
        if(snapshot.scanned!=16 || !snapshot.columnAt(0,0).valid() || voxels.reads>16*40)
            throw new AssertionError("Bounded public cache must populate camera-local columns without a whole-grid scan");
        System.out.println("PASS bathymetry bounded camera-local cache update");
        var moved=field.update(voxels,identity,-31,-32,62.8888889,0);
        if(!moved.columnAt(0,0).valid() || moved.columnAt(32,0).valid()
                || !snapshot.columnAt(0,0).valid())
            throw new AssertionError("Small recenter preserves anchored data and immutable previous snapshot");
        if(field.update(voxels,new Object(),-31,-32,62.8888889,0).columnAt(0,0).valid())
            throw new AssertionError("World identity changes invalidate immediately");
        field.update(voxels,identity,-32,-32,62.8888889,16);
        if(field.update(voxels,identity,-32,-32,63.8888889,0).columnAt(0,0).valid())
            throw new AssertionError("Plane changes invalidate immediately");
        field.update(voxels,identity,-32,-32,62.8888889,16);
        if(field.update(voxels,identity,0,-32,62.8888889,0).columnAt(0,0).valid())
            throw new AssertionError("Teleport invalidates immediately even if old cells overlap");
        field.update(voxels,identity,-32,-32,62.8888889,16);voxels.available=false;
        if(field.update(voxels,identity,-32,-32,62.8888889,0).columnAt(0,0).valid())
            throw new AssertionError("Unloaded previously known cells become unknown immediately");
        System.out.println("PASS bathymetry immutable/recenter/world/plane/teleport/unload cache boundaries");
        field=new BathymetryField();voxels=new Voxels();
        for(int i=0;i<400;i++) {
            int before=voxels.reads;
            snapshot=field.update(voxels,identity,-32,-32,62.8888889,16);
            if(snapshot.scanned>16 || voxels.reads-before>16*40)
                throw new AssertionError("Every update obeys the external voxel-read budget");
        }
        for(int z=-32;z<32;z++) for(int x=-32;x<32;x++)
            if(!snapshot.columnAt(x,z).valid()) throw new AssertionError("Cache must eventually cover the full loaded window");
        voxels.floor=57;
        for(int i=0;i<257;i++) snapshot=field.update(voxels,identity,-32,-32,62.8888889,16);
        for(int z=-32;z<32;z++) for(int x=-32;x<32;x++)
            if(Math.abs(snapshot.columnAt(x,z).depth()-4.8888889)>0.00001)
                throw new AssertionError("Rolling refresh must eventually observe every changed floor");
        System.out.println("PASS bathymetry whole-window bounded fill and fair changed-floor refresh");
    }
}
