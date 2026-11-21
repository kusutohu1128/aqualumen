package dev.aqualumen.physics;

public final class ReceiverSourceVolumeTest {
    private static final class World implements ReceiverSourceVolume.World {
        boolean loaded=true, changed, shadeMissing, stale, wrongIdentity;
        int reads, shades;
        float partialHeight;
        boolean heightDrift;
        boolean twoTops,wrongBatchOrder,wrongBatchExtent;
        int lastBatchSize,missingX=-1;
        boolean cacheCells;
        int validations;
        boolean upperCap,upperDrift;
        float upperHeight;
        final ReceiverCaptureCache<ReceiverSourceVolume.Top,ReceiverField.Cell> cells=new ReceiverCaptureCache<>();
        ReceiverRadianceVolume.Epoch epoch;
        public boolean loaded(int x,int z) { return loaded; }
        public int minY() { return 0; }
        public int maxY() { return 4; }
        public ReceiverField.Cell receiverCell(int x,int y,int z) {
            return cacheCells ? cells.get(new ReceiverSourceVolume.Top(x,y,z),()->readCell(x,y,z)) : readCell(x,y,z);
        }
        private ReceiverField.Cell readCell(int x,int y,int z) {
            reads++;
            if(changed && shades>0 && y==0) return new ReceiverField.Cell(ReceiverField.Kind.OPAQUE,"minecraft:stone");
            if(y==0) return new ReceiverField.Cell(ReceiverField.Kind.OPAQUE,"minecraft:sand");
            if(y==3 && x==0 && upperCap) return new ReceiverField.Cell(ReceiverField.Kind.AIR,"minecraft:air");
            if(x==1 && !twoTops) return new ReceiverField.Cell(ReceiverField.Kind.UNSUPPORTED,"minecraft:seagrass");
            return new ReceiverField.Cell(ReceiverField.Kind.WATER,"minecraft:water");
        }
        public void beginValidation() { validations++; cells.beginValidation(); }
        public boolean fullWater(int x,int y,int z) { return y==1 && (x==0 || twoTops); }
        public float partialWaterHeight(int x,int y,int z) {
            return y==2 && x==0 ? (heightDrift && shades>0 ? partialHeight*.5f : partialHeight) : 0;
        }
        public float upperWaterHeight(int x,int y,int z) {
            return y==3 && x==0 ? (upperDrift && shades>0 ? upperHeight*.5f : upperHeight) : 0;
        }
        public ReceiverSourceVolume.Surface shadeTop(int x,int y,int z) {
            shades++;
            if(shadeMissing || x==missingX) return null;
            var sourceEpoch=stale ? new ReceiverRadianceVolume.Epoch(this,epoch.frame()+1,epoch.resources()) : epoch;
            return new ReceiverSourceVolume.Surface(sourceEpoch,wrongIdentity?"minecraft:stone":"minecraft:sand",
                    new float[]{2+x,3,4,1},new float[]{1,2,3,1});
        }
        public java.util.List<ReceiverSourceVolume.ShadedTop> shadeTops(java.util.List<ReceiverSourceVolume.Top> tops) {
            lastBatchSize=tops.size();
            var results=new java.util.ArrayList<>(ReceiverSourceVolume.World.super.shadeTops(tops));
            if(wrongBatchExtent) return java.util.List.of();
            if(wrongBatchOrder) java.util.Collections.reverse(results);
            return java.util.List.copyOf(results);
        }
    }
    public static void main(String[] args) {
        coordinateHash();
        captureCache();
        upperCap();
        var world=new World(); world.epoch=new ReceiverRadianceVolume.Epoch(world,1,2);
        var schedule=new ReceiverSourceSchedule();
        check(!schedule.reserve(null) && schedule.reserve(world.epoch) && !schedule.reserve(world.epoch),"One attempt per actual frame");
        check(schedule.reserve(new ReceiverRadianceVolume.Epoch(world,2,2))
                && !schedule.reserve(world.epoch),"Fresh frame allowed, older same-resource frame rejected");
        check(schedule.reserve(new ReceiverRadianceVolume.Epoch(world,2,3))
                && schedule.reserve(new ReceiverRadianceVolume.Epoch(new Object(),2,3)),"World/resource changes require fresh work");
        schedule.reset(); check(schedule.reserve(world.epoch),"Pipeline reset clears scheduling state");
        var bounds=new ReceiverField.Bounds(0,0,0,2,3,1);
        var volume=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(volume.cells()[0]==3 && volume.cells()[4]==3 && volume.cells()[8]==2
                && volume.cells()[12]==0 && volume.cells()[16]==0,"Opaque/full/unsupported/partial layout");
        check(world.shades==1 && volume.source()[3]==1 && volume.source()[7]==0
                && volume.faces()[1]==1 && volume.sun()[0]==1,"Only qualified exposed top receives paired supplied RGB");
        check(world.validations==1,"Fresh verification phase begins after shading");
        var surface=world.shadeTop(0,0,0); var values=surface.total(); values[0]=99;
        check(surface.total()[0]==2,"Owned surface channels");
        world.partialHeight=.8888889f;
        var partial=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(partial.cells()[16]==4 && partial.cells()[17]==world.partialHeight && partial.cells()[19]==1
                && partial.source()[19]==0,"Qualified partial height is geometry, never a full cell or surface source");
        var malformed=partial.cells(); malformed[18]=0;
        boolean partialRejected=false;
        try { new ReceiverRadianceVolume(world.epoch,bounds,malformed,partial.source(),partial.sun(),partial.faces()); }
        catch(IllegalArgumentException expected) { partialRejected=true; }
        check(partialRejected,"Missing partial-water qualification rejected");
        world.partialHeight=1.8888889f;
        var cap=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(cap.cells()[16]==4 && cap.cells()[17]==world.partialHeight && cap.source()[19]==0,
                "Underlying cap row retains relative surface height without radiance ownership");
        world.partialHeight=.8888889f;
        world.heightDrift=true; world.shades=0;
        boolean driftRejected=false;
        try { ReceiverSourceVolume.capture(world,bounds,world.epoch); }
        catch(IllegalStateException expected) { driftRejected=true; }
        check(driftRejected,"Fluid-height changes during shading invalidate the capture");
        world.heightDrift=false;
        world.partialHeight=0;
        world.twoTops=true;
        var batch=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(world.lastBatchSize==2 && batch.source()[0]==2 && batch.source()[4]==3
                && batch.source()[3]==1 && batch.source()[7]==1,"Two ordered distinct sources composed in one batch");
        world.missingX=1;
        var missing=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(missing.source()[3]==1 && missing.cells()[4]==3 && missing.source()[7]==0,
                "Unavailable batch lane retains opaque geometry without suppressing qualified neighbor");
        world.missingX=-1;
        for(int negative=0;negative<2;negative++) {
            world.wrongBatchOrder=negative==0; world.wrongBatchExtent=negative==1;
            boolean batchRejected=false;
            try { ReceiverSourceVolume.capture(world,bounds,world.epoch); }
            catch(IllegalStateException expected) { batchRejected=true; }
            check(batchRejected,"Batch order/extent mismatch rejected despite identical material identity");
        }
        world.twoTops=false; world.wrongBatchOrder=false; world.wrongBatchExtent=false;
        for(int negative=0;negative<3;negative++) {
            world.shadeMissing=negative==0; world.stale=negative==1; world.wrongIdentity=negative==2;
            var unavailable=ReceiverSourceVolume.capture(world,bounds,world.epoch);
            check(unavailable.cells()[0]==3 && unavailable.source()[3]==0,"Unready/stale/mismatched first source retains geometry");
        }
        world.shadeMissing=false; world.stale=false; world.wrongIdentity=false;
        world.cacheCells=true; world.changed=true; world.shades=0;
        boolean rejected=false;
        try { ReceiverSourceVolume.capture(world,bounds,world.epoch); } catch(IllegalStateException expected) { rejected=true; }
        check(rejected,"Fresh validation rejects geometry edits concealed by the collection-phase cache");
        world.loaded=false; world.reads=0; world.shades=0;
        var unloaded=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(world.reads==0 && world.shades==0 && unloaded.cells()[0]==0,"No unloaded reads or source work");
        System.out.println("PASS bounded source-volume CPU composition: supplied paired RGB, exposed-top/full-water geometry, unavailable/stale/identity/change/unloaded controls; not live publication or reflection acceptance");
    }
    private static void captureCache() {
        var cache=new ReceiverCaptureCache<Integer,Integer>(2);
        int[] current={10};
        check(cache.get(1,()->current[0])==10,"Capture cache initial read"); current[0]=20;
        check(cache.get(1,()->current[0])==10 && cache.reads()==1,"Repeated phase queries do not re-read the world");
        cache.beginValidation();
        check(cache.get(1,()->current[0])==20 && cache.reads()==2,"Validation discards collection values and reads fresh state");
        cache.get(2,()->30);
        boolean bounded=false;
        try { cache.get(3,()->40); } catch(IllegalStateException expected) { bounded=true; }
        check(bounded,"Capture cache is bounded");
        var rejected=new java.util.concurrent.atomic.AtomicBoolean();
        var other=new Thread(()-> {
            try { cache.get(1,()->99); } catch(IllegalStateException expected) { rejected.set(true); }
        });
        other.start();
        try { other.join(); } catch(InterruptedException interrupted) { throw new AssertionError(interrupted); }
        check(rejected.get(),"Capture cache rejects another thread");
        cache.close(); cache.close();
        boolean closed=false;
        try { cache.get(1,()->99); } catch(IllegalStateException expected) { closed=true; }
        check(closed,"Capture cache cannot leak into a later capture");
    }
    private static void upperCap() {
        var world=new World(); world.epoch=new ReceiverRadianceVolume.Epoch(world,1,1);
        world.upperCap=true; world.upperHeight=-.1111111f; world.partialHeight=.8888889f;
        var bounds=new ReceiverField.Bounds(0,0,0,2,4,1);
        var volume=ReceiverSourceVolume.capture(world,bounds,world.epoch);
        check(volume.cells()[24]==5 && volume.cells()[25]==world.upperHeight
                && volume.source()[27]==0 && volume.sun()[27]==0 && volume.faces()[27]==0,
                "Upper crest cap is qualified geometry, never a full water cell or radiance owner");
        var malformed=volume.cells(); malformed[25]=0;
        boolean rejected=false;
        try { new ReceiverRadianceVolume(world.epoch,bounds,malformed,volume.source(),volume.sun(),volume.faces()); }
        catch(IllegalArgumentException expected) { rejected=true; }
        check(rejected,"Unqualified upper-cap mean height rejected");
        world.upperDrift=true; world.shades=0;
        boolean changed=false;
        try { ReceiverSourceVolume.capture(world,bounds,world.epoch); }
        catch(IllegalStateException expected) { changed=true; }
        check(changed,"Upper-cap changes during shading invalidate publication");
    }
    private static void coordinateHash() {
        var hashes=new java.util.HashSet<Integer>();
        var keys=new java.util.HashMap<ReceiverSourceVolume.Top,Integer>();
        int count=0;
        for(int dz=0;dz<87;dz++) for(int dy=0;dy<36;dy++) for(int dx=0;dx<87;dx++) {
            var key=new ReceiverSourceVolume.Top(405+dx,32+dy,-427+dz);
            hashes.add(key.hashCode()); keys.put(key,count++);
        }
        check(hashes.size()>count*.99,"Coordinate hashes must not collapse the live field's spatial lattice");
        check(keys.size()==count,"Coordinate hash collisions must not merge distinct cells");
        int index=0;
        for(int dz=0;dz<87;dz++) for(int dy=0;dy<36;dy++) for(int dx=0;dx<87;dx++)
            check(keys.get(new ReceiverSourceVolume.Top(405+dx,32+dy,-427+dz))==index++,
                    "Equal coordinate keys must retrieve their exact source index");
        var extreme=new ReceiverSourceVolume.Top(Integer.MIN_VALUE,Integer.MAX_VALUE,-1);
        var equal=new ReceiverSourceVolume.Top(Integer.MIN_VALUE,Integer.MAX_VALUE,-1);
        check(extreme.equals(equal) && extreme.hashCode()==equal.hashCode(),"Extreme coordinates preserve hash equality");
        check(!extreme.equals(new ReceiverSourceVolume.Top(Integer.MIN_VALUE,Integer.MAX_VALUE,0)),
                "Coordinate hash must not replace equality");
        System.out.println("PASS coordinate-key hash distribution: "+hashes.size()+" distinct hashes / "+count+" cells; exact fresh-key lookup, CPU only");
    }
    private static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
}
