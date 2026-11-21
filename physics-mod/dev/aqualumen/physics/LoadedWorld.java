package dev.aqualumen.physics;

import java.lang.reflect.*;

/** Pinned 1.21.1 intermediary API. Retains only already-present client chunks for this scan. */
final class LoadedWorld implements BathymetryField.World {
    private static final class Api {
        final Method manager,chunk,block,fluid,kind,height,empty,air,full,solid,bottom,top,collision,shapeEmpty;
        final Constructor<?> position;
        final Object fullStatus,still,flowing;
        Api() throws ReflectiveOperationException {
            Class<?> clientWorld=Class.forName("net.minecraft.class_638");
            Class<?> view=Class.forName("net.minecraft.class_1922");
            Class<?> pos=Class.forName("net.minecraft.class_2338");
            Class<?> status=Class.forName("net.minecraft.class_2806");
            manager=clientWorld.getMethod("method_2935");
            // ClientWorld.isChunkLoaded is unconditionally true in this version. Never use it.
            chunk=Class.forName("net.minecraft.class_631").getMethod("method_2857",int.class,int.class,status,boolean.class);
            fullStatus=status.getField("field_12803").get(null);
            block=view.getMethod("method_8320",pos);fluid=view.getMethod("method_8316",pos);
            position=pos.getConstructor(int.class,int.class,int.class);
            Class<?> fs=Class.forName("net.minecraft.class_3610");
            kind=fs.getMethod("method_15772");height=fs.getMethod("method_20785");empty=fs.getMethod("method_15769");
            Class<?> fluids=Class.forName("net.minecraft.class_3612");
            still=fluids.getField("field_15910").get(null);flowing=fluids.getField("field_15909").get(null);
            Class<?> state=Class.forName("net.minecraft.class_2680");
            air=state.getMethod("method_26215");
            full=state.getMethod("method_26234",view,pos);solid=state.getMethod("method_26212",view,pos);
            collision=state.getMethod("method_26220",view,pos);
            shapeEmpty=Class.forName("net.minecraft.class_265").getMethod("method_1110");
            Class<?> limits=Class.forName("net.minecraft.class_5539");
            bottom=limits.getMethod("method_31607");top=limits.getMethod("method_31600");
        }
    }
    private static Api api;
    private final Object manager;
    private final ReceiverChunkLease<Object> chunks;
    private final int minimum,maximum;
    LoadedWorld(Object world) throws ReflectiveOperationException {
        if(api==null) api=new Api();
        manager=api.manager.invoke(world);
        chunks=new ReceiverChunkLease<>((sectionX,sectionZ) -> api.chunk.invoke(manager,sectionX,sectionZ,api.fullStatus,false));
        minimum=(int)api.bottom.invoke(world);maximum=(int)api.top.invoke(world);
    }
    public int minY() {return minimum;}
    public int maxY() {return maximum;}
    // Package boundary for the optional receiver adapter; same retained FULL,false lookup.
    Object existing(int x,int z) throws ReflectiveOperationException {
        return chunks.existing(x,z);
    }
    void validateChunks() throws ReflectiveOperationException { chunks.validate(); }
    public boolean loaded(int x,int z) {
        try {return existing(x,z)!=null;}
        catch(ReflectiveOperationException e) {throw new IllegalStateException("Loaded chunk boundary unavailable",e);}
    }
    public BathymetryField.Cell cell(int x,int y,int z) {
        try {
            Object retained=existing(x,z);
            if(retained==null || y<minimum || y>=maximum) return new BathymetryField.Cell(false,0,false);
            Object pos=api.position.newInstance(x,y,z);
            Object state=api.block.invoke(retained,pos),fluid=api.fluid.invoke(retained,pos);
            Object kind=api.kind.invoke(fluid);
            boolean water=kind==api.still || kind==api.flowing;
            // Empty-collision kelp/seagrass may contain continuous water; slabs/stairs/fences may not.
            boolean clearWater=water && (boolean)api.shapeEmpty.invoke(api.collision.invoke(state,retained,pos));
            boolean floor=!water && (boolean)api.empty.invoke(fluid) && !(boolean)api.air.invoke(state)
                    && (boolean)api.full.invoke(state,retained,pos) && (boolean)api.solid.invoke(state,retained,pos);
            return new BathymetryField.Cell(water,clearWater?(float)api.height.invoke(fluid):water?Float.NaN:0,floor);
        } catch(ReflectiveOperationException e) {throw new IllegalStateException("Voxel boundary unavailable",e);}
    }
}
