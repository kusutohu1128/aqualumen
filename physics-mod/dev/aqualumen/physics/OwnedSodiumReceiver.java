package dev.aqualumen.physics;

import net.irisshaders.iris.shaderpack.materialmap.WorldRenderingSettings;

public final class OwnedSodiumReceiver {
    private static final ReceiverMemberCache members=new ReceiverMemberCache();
    private OwnedSodiumReceiver() { }
    public static ReceiverSodiumScope.Snapshot capture(ReceiverRadianceVolume.Epoch epoch, int x, int y, int z)
            throws ReflectiveOperationException {
        try(var session=new Session(epoch)) { return session.capture(x,y,z); }
    }
    public static final class Session implements AutoCloseable {
        private final ReceiverRadianceVolume.Epoch epoch;
        private final Thread owner=Thread.currentThread();
        private Object clones,cache,buffers,renderer,slice;
        private LoadedReceiverWorld geometry;
        private Section section;
        private boolean closed;
        private int captures,sectionCopies;
        private record Section(int x,int y,int z) { }
        private record Captured(ReceiverSodiumScope.Snapshot top, ReceiverSodiumScope.GeometrySnapshot geometry) { }
        public Session(ReceiverRadianceVolume.Epoch epoch) { this.epoch=java.util.Objects.requireNonNull(epoch); }
        public int captures() { return captures; }
        public int sectionCopies() { return sectionCopies; }
        public ReceiverSodiumScope.Snapshot capture(int x,int y,int z) throws ReflectiveOperationException {
            var result = captureOwned(x,y,z,false);
            return result == null ? null : result.top();
        }
        public ReceiverSodiumScope.GeometrySnapshot captureGeometry(int x,int y,int z) throws ReflectiveOperationException {
            var result = captureOwned(x,y,z,true);
            return result == null ? null : result.geometry();
        }
        private Captured captureOwned(int x,int y,int z,boolean modelGeometry) throws ReflectiveOperationException {
        var now=ReceiverRadianceBridge.epoch();
        if(closed || Thread.currentThread()!=owner || now==null || epoch.world()!=now.world()
                || epoch.frame()!=now.frame() || epoch.resources()!=now.resources())
            throw new IllegalStateException("Owned receiver meshing session expired");
        if (!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
            throw new IllegalStateException("Owned receiver meshing outside render thread");
        Object client = Class.forName("net.minecraft.class_310").getMethod("method_1551").invoke(null);
        if (client.getClass().getField("field_1687").get(client) != epoch.world() || !WorldRenderingSettings.INSTANCE.shouldUseSeparateAo())
            throw new IllegalStateException("Receiver world/separate-AO owner unavailable");
        if(geometry==null) geometry=new LoadedReceiverWorld(epoch.world());
        if (y < geometry.minY() || y >= geometry.maxY()) return null;
        for (int sectionZ = Math.floorDiv(z,16)-1; sectionZ <= Math.floorDiv(z,16)+1; sectionZ++)
            for (int sectionX = Math.floorDiv(x,16)-1; sectionX <= Math.floorDiv(x,16)+1; sectionX++)
                if (!geometry.loaded(sectionX*16,sectionZ*16)) throw new IllegalStateException("Receiver neighbor chunk unavailable: " + sectionX + "," + sectionZ);
        var cell = geometry.receiverCell(x,y,z);
        if (modelGeometry ? cell.kind() != ReceiverField.Kind.UNSUPPORTED || !java.util.Set.of(
                "minecraft:seagrass","minecraft:tall_seagrass","minecraft:kelp","minecraft:kelp_plant").contains(cell.blockId())
                : cell.kind() != ReceiverField.Kind.OPAQUE) return null;
        try {
            if(clones==null) clones=create("net.caffeinemc.mods.sodium.client.world.cloned.ClonedChunkSectionCache",epoch.world());
            if(cache==null) cache=create("net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockRenderCache",client,epoch.world());
            if(buffers==null) buffers=create("net.caffeinemc.mods.sodium.client.render.chunk.compile.ChunkBuildBuffers",WorldRenderingSettings.INSTANCE.getVertexFormat());
            var next=new Section(Math.floorDiv(x,16),Math.floorDiv(y,16),Math.floorDiv(z,16));
            if(!next.equals(section)) {
                invoke(cache,"cleanup"); section=null; slice=null;
                Object position=create("net.minecraft.class_4076",next.x(),next.y(),next.z());
                Object context=invokeStatic("net.caffeinemc.mods.sodium.client.world.LevelSlice","prepare",epoch.world(),position,clones);
                if(context==null) throw new IllegalStateException("Receiver cloned section unavailable");
                invoke(cache,"init",context);
                slice=invoke(cache,"getWorldSlice");
                if(ReceiverSodiumIntake.field(slice,"level")!=epoch.world()) throw new IllegalStateException("Cloned receiver world mismatch");
                section=next; sectionCopies++;
            }
            invoke(buffers,"init",create("net.caffeinemc.mods.sodium.client.render.chunk.data.BuiltSectionInfo$Builder"),0);
            renderer = invoke(cache,"getBlockRenderer");
            invoke(renderer,"prepare",buffers,slice,null);
            Object state = invoke(slice,"getBlockState",x,y,z);
            Object model = invoke(invoke(cache,"getBlockModels"),"method_3335",state);
            Object position = create("net.minecraft.class_2338",x,y,z);
            Object local = create("net.minecraft.class_2338",Math.floorMod(x,16),Math.floorMod(y,16),Math.floorMod(z,16));
            Captured result;
            try (var scope = modelGeometry ? ReceiverSodiumScope.openGeometry(epoch,renderer,x,y,z,state.toString())
                    : ReceiverSodiumScope.open(epoch,renderer,x,y,z,state.toString())) {
                invoke(buffers,"beginBlock",0,(byte)0,(byte)0,Math.floorMod(x,16),Math.floorMod(y,16),Math.floorMod(z,16));
                try { invoke(renderer,"renderModel",model,state,position,local); }
                finally { invoke(buffers,"endBlock"); }
                if (modelGeometry) {
                    var modelFaces = scope.finishGeometry();
                    if (modelFaces == null) throw new IllegalStateException("Owned receiver model unavailable: " + scope.status());
                    result = new Captured(null,modelFaces);
                } else {
                    var top = scope.finish();
                    if (top == null) throw new IllegalStateException("Owned receiver face unavailable: " + scope.status());
                    if (top.packed().size() != 4) throw new IllegalStateException("Owned Iris encoder output unavailable");
                    result = new Captured(top,null);
                }
            }
            captures++;
            return cell.equals(geometry.receiverCell(x,y,z)) ? result : null;
        } finally {
            if(renderer!=null) invoke(renderer,"release");
        }
        }
        public void close() {
            if(Thread.currentThread()!=owner) throw new IllegalStateException("Owned receiver session close outside owner");
            if(closed) return;
            closed=true;
            try {
                try { if(renderer!=null) invoke(renderer,"release"); }
                finally {
                    try { if(cache!=null) invoke(cache,"cleanup"); }
                    finally { if(buffers!=null) invoke(buffers,"destroy"); }
                }
            } catch(ReflectiveOperationException error) { throw new IllegalStateException("Owned receiver session cleanup failed",error); }
            finally { clones=null; cache=null; buffers=null; renderer=null; slice=null; section=null; geometry=null; }
        }
    }

    private static Object create(String name, Object... arguments) throws ReflectiveOperationException {
        return members.constructor(Class.forName(name),arguments).newInstance(arguments);
    }
    private static Object invoke(Object owner, String name, Object... arguments) throws ReflectiveOperationException {
        return members.method(owner.getClass(),name,false,arguments).invoke(owner,arguments);
    }
    private static Object invokeStatic(String owner, String name, Object... arguments) throws ReflectiveOperationException {
        return members.method(Class.forName(owner),name,true,arguments).invoke(null,arguments);
    }
}
