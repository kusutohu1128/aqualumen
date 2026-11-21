package dev.aqualumen.physics;

public final class LoadedReceiverSourceWorld implements ReceiverSourceVolume.World, AutoCloseable {
    private final LoadedReceiverWorld geometry;
    private final ReceiverRadianceVolume.Epoch epoch;
    private final ReceiverTerrainState terrain;
    private final ReceiverLightingState lighting;
    private final ReceiverSourceDraw.Session sourceSession;
    private final OwnedSodiumReceiver.Session meshSession;
    private final ReceiverCaptureCache<Long,Boolean> loadedCache=new ReceiverCaptureCache<>();
    private final ReceiverVoxelCache<ReceiverField.Cell> cellCache;
    private final ReceiverVoxelCache<Float> heightCache;
    private final ReceiverVoxelCache<Boolean> fullCache;
    private final ReceiverVoxelCache<Float> partialCache;
    private final ReceiverVoxelCache<Float> upperCache;
    private final int minY,maxY;
    private final java.util.List<ReceiverModelStateWitness.Owner> modelOwners=new java.util.ArrayList<>();
    private int sourceBatches;
    private long meshingNanos,drawNanos;
    private final Thread owner=Thread.currentThread();

    public LoadedReceiverSourceWorld(ReceiverRadianceVolume.Epoch epoch, ReceiverTerrainState terrain,
                                     ReceiverLightingState lighting,ReceiverRunPublisher.Window window) throws ReflectiveOperationException {
        if(!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
            throw new IllegalStateException("Receiver source capture outside render thread");
        this.epoch=epoch; this.terrain=terrain; this.lighting=lighting;
        cellCache=cache(window);heightCache=cache(window);
        fullCache=cache(window);partialCache=cache(window);upperCache=cache(window);
        geometry=new LoadedReceiverWorld(epoch.world());
        minY=geometry.minY(); maxY=geometry.maxY();
        sourceSession=new ReceiverSourceDraw.Session(epoch);
        meshSession=new OwnedSodiumReceiver.Session(epoch);
    }
    private static <Value> ReceiverVoxelCache<Value> cache(ReceiverRunPublisher.Window window) {
        return new ReceiverVoxelCache<>(Math.subtractExact(window.x(),2),Math.subtractExact(window.y(),3),
                Math.subtractExact(window.z(),2),window.width()+4,window.height()+6,window.depth()+4);
    }
    private void owner() {
        if(Thread.currentThread()!=owner || !ReceiverRadianceBridge.lightingCurrent(lighting))
            throw new IllegalStateException("Receiver source owner expired");
    }
    public boolean loaded(int x,int z) {
        owner(); long key=((long)Math.floorDiv(x,16)<<32)^(Math.floorDiv(z,16)&0xffffffffL);
        return loadedCache.get(key,()->geometry.loaded(x,z));
    }
    public int minY() { owner(); return minY; }
    public int maxY() { owner(); return maxY; }
    public ReceiverField.Cell receiverCell(int x,int y,int z) {
        owner(); return cellCache.get(x,y,z,()->geometry.receiverCell(x,y,z));
    }
    private float fluidHeight(int x,int y,int z) {
        owner(); return heightCache.get(x,y,z,()->geometry.fluidHeight(x,y,z));
    }
    public boolean fullWater(int x,int y,int z) {
        owner(); return fullCache.get(x,y,z,()->readFullWater(x,y,z));
    }
    private boolean readFullWater(int x,int y,int z) {
        return loaded(x,z) && y>=minY() && y+2<maxY() && receiverCell(x,y,z).kind()==ReceiverField.Kind.WATER
                && receiverCell(x,y+1,z).kind()==ReceiverField.Kind.WATER && receiverCell(x,y+2,z).kind()==ReceiverField.Kind.WATER;
    }
    public ReceiverSourceVolume.Surface shadeTop(int x,int y,int z) {
        return shadeTops(java.util.List.of(new ReceiverSourceVolume.Top(x,y,z))).get(0).surface();
    }
    public java.util.List<ReceiverSourceVolume.ShadedTop> shadeTops(java.util.List<ReceiverSourceVolume.Top> tops) {
        owner();
        var requests=java.util.List.copyOf(tops);
        var points=new java.util.ArrayList<ReceiverSourceDraw.Point>();
        var indices=new java.util.ArrayList<Integer>();
        var identities=new java.util.ArrayList<ReceiverField.Cell>();
        var surfaces=new java.util.ArrayList<ReceiverSourceVolume.ShadedTop>();
        var order=new java.util.ArrayList<Integer>();
        for(int index=0;index<requests.size();index++) {
            surfaces.add(new ReceiverSourceVolume.ShadedTop(requests.get(index),null)); order.add(index);
        }
        order.sort(java.util.Comparator.<Integer>comparingInt(index->Math.floorDiv(requests.get(index).y(),16))
                .thenComparingInt(index->Math.floorDiv(requests.get(index).z(),16))
                .thenComparingInt(index->Math.floorDiv(requests.get(index).x(),16)));
        try {
            long meshStarted=System.nanoTime();
            for(int index:order) {
                owner(); var top=requests.get(index);
                var cell=receiverCell(top.x(),top.y(),top.z());
                if(cell.kind()!=ReceiverField.Kind.OPAQUE || !fullWater(top.x(),top.y()+1,top.z())) continue;
                var face=meshSession.capture(top.x(),top.y(),top.z());
                var decoded=terrain.decode(face);
                if(decoded==null) continue;
                var witness=new ReceiverModelStateWitness.Owner(top.x(),top.y(),top.z(),face.state());
                if(!witness.state().equals(geometry.blockState(top.x(),top.y(),top.z())))
                    throw new IllegalStateException("Cloned source model differs from current owner state");
                modelOwners.add(witness);
                points.add(new ReceiverSourceDraw.Point(face,decoded.sample(.5,.5))); indices.add(index); identities.add(cell);
            }
            meshingNanos+=System.nanoTime()-meshStarted;
            for(int start=0;start<points.size();start+=4096) {
                owner(); int end=Math.min(start+4096,points.size());
                long drawStarted=System.nanoTime();
                var results=ReceiverSourceDraw.points(sourceSession,points.subList(start,end),terrain,lighting,epoch);
                sourceBatches++;
                for(int point=start;point<end;point++) {
                    int index=indices.get(point); var top=requests.get(index); var cell=identities.get(point);
                    var result=results.get(point-start);
                    if(result.total().get(3)!=1 || !cell.equals(receiverCell(top.x(),top.y(),top.z()))) continue;
                    float[] total=new float[4], sun=new float[4];
                    for(int channel=0;channel<4;channel++) { total[channel]=result.total().get(channel); sun[channel]=result.sun().get(channel); }
                    surfaces.set(index,new ReceiverSourceVolume.ShadedTop(top,new ReceiverSourceVolume.Surface(epoch,cell.blockId(),total,sun)));
                }
                drawNanos+=System.nanoTime()-drawStarted;
            }
            owner(); return java.util.List.copyOf(surfaces);
        } catch(ReflectiveOperationException error) { throw new IllegalStateException("Owned receiver source boundary unavailable",error); }
    }
    public float partialWaterHeight(int x,int y,int z) {
        owner(); return partialCache.get(x,y,z,()->readPartialWaterHeight(x,y,z));
    }
    private float readPartialWaterHeight(int x,int y,int z) {
        owner();
        if(!loaded(x,z) || y<minY() || y>=maxY() || receiverCell(x,y,z).kind()!=ReceiverField.Kind.WATER) return 0;
        float height=fluidHeight(x,y,z);
        if(height>0 && height<1) return flatTopHeight(x,y,z);
        if(height==1 && y+1<maxY()) {
            float top=flatTopHeight(x,y+1,z);
            if(top>0) return 1+top;
        }
        return 0;
    }
    private float flatTopHeight(int x,int y,int z) {
        if(y-2<minY() || y+1>=maxY() || !loaded(x,z) || receiverCell(x,y,z).kind()!=ReceiverField.Kind.WATER) return 0;
        float height=fluidHeight(x,y,z);
        if(height<=0 || height>=1) return 0;
        for(int dz=-1;dz<=1;dz++) for(int dx=-1;dx<=1;dx++) {
            int wx=x+dx,wz=z+dz;
            if(!loaded(wx,wz) || receiverCell(wx,y,wz).kind()!=ReceiverField.Kind.WATER
                    || receiverCell(wx,y+1,wz).kind()!=ReceiverField.Kind.AIR
                    || receiverCell(wx,y-1,wz).kind()!=ReceiverField.Kind.WATER || fluidHeight(wx,y-1,wz)!=1
                    || receiverCell(wx,y-2,wz).kind()!=ReceiverField.Kind.WATER || fluidHeight(wx,y-2,wz)!=1
                    || fluidHeight(wx,y,wz)!=height) return 0;
        }
        return height;
    }
    public float upperWaterHeight(int x,int y,int z) {
        owner(); return upperCache.get(x,y,z,()-> {
            if(!loaded(x,z) || y-1<minY() || y>=maxY() || receiverCell(x,y,z).kind()!=ReceiverField.Kind.AIR) return 0f;
            float height=partialWaterHeight(x,y-1,z);
            return height>0 && height<1 ? height-1 : 0f;
        });
    }
    public int sourceBatches() { return sourceBatches; }
    public long meshingNanos() { owner(); return meshingNanos; }
    public long drawNanos() { owner(); return drawNanos; }
    public int geometryReads() { return cellCache.reads()+heightCache.reads(); }
    public void beginValidation() {
        owner(); geometry.validateChunks();
        ReceiverModelStateWitness.verify(modelOwners,
                model->geometry.blockState(model.x(),model.y(),model.z()),this::owner);
        geometry.validateChunks(); loadedCache.beginValidation(); cellCache.beginValidation(); heightCache.beginValidation();
        fullCache.beginValidation(); partialCache.beginValidation(); upperCache.beginValidation();
    }
    public int meshCaptures() { return meshSession.captures(); }
    public int sectionCopies() { return meshSession.sectionCopies(); }
    public void close() {
        modelOwners.clear();
        loadedCache.close(); cellCache.close(); heightCache.close(); fullCache.close(); partialCache.close(); upperCache.close();
        try { sourceSession.close(); }
        finally { meshSession.close(); }
    }
}
