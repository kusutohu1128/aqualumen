package dev.aqualumen.physics;

import java.lang.reflect.*;
import java.lang.invoke.*;

/** Optional pinned 1.21.1 geometry adapter. Not registered, scheduled or uploaded yet. */
final class LoadedReceiverWorld implements ReceiverField.World {
    private static final class Api {
        final MethodHandle position, block, fluid, blockType, blockId, kind, empty, full, solid, collision, shapeEmpty, fluidHeight;
        final Object blockRegistry, still, flowing;
        Api() throws ReflectiveOperationException {
            Class<?> pos = Class.forName("net.minecraft.class_2338"), view = Class.forName("net.minecraft.class_1922");
            position = geometryConstructor(pos.getConstructor(int.class, int.class, int.class));
            block = geometryMethod(view.getMethod("method_8320", pos)); fluid = geometryMethod(view.getMethod("method_8316", pos));
            Class<?> state = Class.forName("net.minecraft.class_2680"), fs = Class.forName("net.minecraft.class_3610");
            blockType = geometryMethod(state.getMethod("method_26204"));
            blockId = geometryMethod(Class.forName("net.minecraft.class_2378").getMethod("method_10221", Object.class));
            blockRegistry = Class.forName("net.minecraft.class_7923").getField("field_41175").get(null);
            kind = geometryMethod(fs.getMethod("method_15772")); empty = geometryMethod(fs.getMethod("method_15769"));
            fluidHeight = geometryMethod(fs.getMethod("method_15763",view,pos));
            Class<?> fluids = Class.forName("net.minecraft.class_3612");
            still = fluids.getField("field_15910").get(null); flowing = fluids.getField("field_15909").get(null);
            full = geometryMethod(state.getMethod("method_26234", view, pos)); solid = geometryMethod(state.getMethod("method_26212", view, pos));
            collision = geometryMethod(state.getMethod("method_26220", view, pos));
            shapeEmpty = geometryMethod(Class.forName("net.minecraft.class_265").getMethod("method_1110"));
        }
    }
    private static Api api;
    static MethodHandle geometryConstructor(Constructor<?> constructor) throws IllegalAccessException {
        return MethodHandles.publicLookup().unreflectConstructor(constructor)
                .asType(MethodType.methodType(Object.class,int.class,int.class,int.class));
    }
    static MethodHandle geometryMethod(Method method) throws IllegalAccessException {
        if(Modifier.isStatic(method.getModifiers())) throw new IllegalArgumentException("Geometry methods must have an instance owner");
        Class<?>[] parameters=method.getParameterTypes();
        Class<?>[] erased=new Class<?>[parameters.length+1]; erased[0]=Object.class;
        for(int index=0;index<parameters.length;index++) erased[index+1]=parameters[index].isPrimitive()?parameters[index]:Object.class;
        Class<?> result=method.getReturnType();
        return MethodHandles.publicLookup().unreflect(method)
                .asType(MethodType.methodType(result.isPrimitive()?result:Object.class,erased));
    }
    private final LoadedWorld chunks;
    LoadedReceiverWorld(Object world) throws ReflectiveOperationException {
        if (api == null) api = new Api();
        chunks = new LoadedWorld(world);
    }
    public boolean loaded(int x, int z) { return chunks.loaded(x, z); }
    public int minY() { return chunks.minY(); }
    public int maxY() { return chunks.maxY(); }
    public void validateChunks() {
        try { chunks.validateChunks(); }
        catch (ReflectiveOperationException error) { throw new IllegalStateException("Receiver chunk validation unavailable",error); }
    }
    public ReceiverWaterVolume.Observation waterVolume(int x,int y,int z) {
        try {
            Object retained=chunks.existing(x,z);
            if (retained==null || y<minY() || y>=maxY())
                return new ReceiverWaterVolume.Observation(false,"","",false,0,false);
            Object position=(Object)api.position.invokeExact(x,y,z);
            Object state=(Object)api.block.invokeExact(retained,position),fluid=(Object)api.fluid.invokeExact(retained,position);
            Object kind=(Object)api.kind.invokeExact(fluid);
            String id=((Object)api.blockId.invokeExact(api.blockRegistry,(Object)api.blockType.invokeExact(state))).toString();
            float height=(float)api.fluidHeight.invokeExact(fluid,retained,position);
            boolean clear=(boolean)api.shapeEmpty.invokeExact((Object)api.collision.invokeExact(state,retained,position));
            return new ReceiverWaterVolume.Observation(true,id,state.toString(),kind==api.still || kind==api.flowing,height,clear);
        } catch (Throwable error) { throw new IllegalStateException("Receiver fluid-volume observation unavailable",error); }
    }
    public String blockState(int x,int y,int z) {
        try {
            Object retained=chunks.existing(x,z);
            if (retained==null || y<minY() || y>=maxY()) return null;
            Object position=(Object)api.position.invokeExact(x,y,z);
            return ((Object)api.block.invokeExact(retained,position)).toString();
        } catch (Throwable error) { throw new IllegalStateException("Receiver model state unavailable",error); }
    }
    public float fluidHeight(int x,int y,int z) {
        try {
            Object retained=chunks.existing(x,z);
            if(retained==null || y<minY() || y>=maxY()) return 0;
            Object pos=(Object)api.position.invokeExact(x,y,z), fluid=(Object)api.fluid.invokeExact(retained,pos);
            float height=(float)api.fluidHeight.invokeExact(fluid,retained,pos);
            return Float.isFinite(height) && height>=0 && height<=1 ? height : 0;
        } catch(Throwable error) { throw new IllegalStateException("Pinned fluid-height boundary unavailable",error); }
    }
    public ReceiverField.Cell receiverCell(int x, int y, int z) {
        try {
            Object retained = chunks.existing(x, z);
            if (retained == null || y < minY() || y >= maxY()) return ReceiverField.Cell.UNKNOWN;
            Object pos = (Object)api.position.invokeExact(x, y, z);
            Object state = (Object)api.block.invokeExact(retained, pos), fluid = (Object)api.fluid.invokeExact(retained, pos);
            Object kind = (Object)api.kind.invokeExact(fluid);
            String id = ((Object)api.blockId.invokeExact(api.blockRegistry, (Object)api.blockType.invokeExact(state))).toString();
            boolean water = kind == api.still || kind == api.flowing;
            boolean fluidEmpty = (boolean)api.empty.invokeExact(fluid);
            boolean emptyShape = (boolean)api.shapeEmpty.invokeExact((Object)api.collision.invokeExact(state, retained, pos));
            boolean fullSolid = ReceiverField.needsFullSolid(id, water, fluidEmpty)
                    && (boolean)api.full.invokeExact(state, retained, pos) && (boolean)api.solid.invokeExact(state, retained, pos);
            return ReceiverField.classifyVanilla(id, water, fluidEmpty, emptyShape, fullSolid);
        } catch (Throwable e) {
            throw new IllegalStateException("Pinned receiver geometry boundary unavailable", e);
        }
    }
}
