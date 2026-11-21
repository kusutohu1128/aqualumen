package dev.aqualumen.physics;

import java.lang.reflect.*;

/** Optional pinned 1.21.1 geometry adapter. Not registered, scheduled or uploaded yet. */
final class LoadedReceiverWorld implements ReceiverField.World {
    private static final class Api {
        final Constructor<?> position;
        final Method block, fluid, blockType, blockId, kind, empty, full, solid, collision, shapeEmpty;
        final Object blockRegistry, still, flowing;
        Api() throws ReflectiveOperationException {
            Class<?> pos = Class.forName("net.minecraft.class_2338"), view = Class.forName("net.minecraft.class_1922");
            position = pos.getConstructor(int.class, int.class, int.class);
            block = view.getMethod("method_8320", pos); fluid = view.getMethod("method_8316", pos);
            Class<?> state = Class.forName("net.minecraft.class_2680"), fs = Class.forName("net.minecraft.class_3610");
            blockType = state.getMethod("method_26204");
            blockId = Class.forName("net.minecraft.class_2378").getMethod("method_10221", Object.class);
            blockRegistry = Class.forName("net.minecraft.class_7923").getField("field_41175").get(null);
            kind = fs.getMethod("method_15772"); empty = fs.getMethod("method_15769");
            Class<?> fluids = Class.forName("net.minecraft.class_3612");
            still = fluids.getField("field_15910").get(null); flowing = fluids.getField("field_15909").get(null);
            full = state.getMethod("method_26234", view, pos); solid = state.getMethod("method_26212", view, pos);
            collision = state.getMethod("method_26220", view, pos);
            shapeEmpty = Class.forName("net.minecraft.class_265").getMethod("method_1110");
        }
    }
    private static Api api;
    private final LoadedWorld chunks;
    LoadedReceiverWorld(Object world) throws ReflectiveOperationException {
        if (api == null) api = new Api();
        chunks = new LoadedWorld(world);
    }
    public boolean loaded(int x, int z) { return chunks.loaded(x, z); }
    public int minY() { return chunks.minY(); }
    public int maxY() { return chunks.maxY(); }
    public ReceiverField.Cell receiverCell(int x, int y, int z) {
        try {
            Object retained = chunks.existing(x, z);
            if (retained == null || y < minY() || y >= maxY()) return ReceiverField.Cell.UNKNOWN;
            Object pos = api.position.newInstance(x, y, z);
            Object state = api.block.invoke(retained, pos), fluid = api.fluid.invoke(retained, pos);
            Object kind = api.kind.invoke(fluid);
            String id = api.blockId.invoke(api.blockRegistry, api.blockType.invoke(state)).toString();
            boolean emptyShape = (boolean)api.shapeEmpty.invoke(api.collision.invoke(state, retained, pos));
            boolean fullSolid = (boolean)api.full.invoke(state, retained, pos) && (boolean)api.solid.invoke(state, retained, pos);
            return ReceiverField.classifyVanilla(id, kind == api.still || kind == api.flowing,
                    (boolean)api.empty.invoke(fluid), emptyShape, fullSolid);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Pinned receiver geometry boundary unavailable", e);
        }
    }
}
