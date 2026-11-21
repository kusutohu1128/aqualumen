package dev.aqualumen.bench;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Read-only observation of existing Iris targets; call on the render thread. */
public final class RenderTargetSnapshot {
    private static final int[] INDICES = {0, 4, 5, 6, 7, 8};
    private RenderTargetSnapshot() {}

    /** Only the external Iris/OpenGL boundary is injectable for CPU tests. */
    public interface SystemBoundary {
        Inventory existingTargets() throws Exception;
        int textureBinding2D() throws Exception;
        boolean textureExists(int texture) throws Exception;
        void bindTexture2D(int texture) throws Exception;
        TextureLevel textureLevel() throws Exception;
    }

    public record Target(String declaredFormat, int mainTexture, int altTexture, int width, int height) {}
    public record Inventory(int renderTargetCount, Map<Integer, Target> targets) {}
    public record TextureLevel(int actualFormat, int width, int height) {}

    public static Map<String, Object> capture() {
        return capture(new ReflectedBoundary());
    }

    public static Map<String, Object> capture(SystemBoundary boundary) {
        Map<String, Object> result = new LinkedHashMap<>();
        List<Map<String, Object>> queries = new ArrayList<>();
        result.put("available", false);
        result.put("queries", queries);
        result.put("bindingRestored", false);
        Integer savedBinding = null;
        try {
            Inventory inventory = boundary.existingTargets();
            if (inventory == null || inventory.targets() == null || inventory.renderTargetCount() <= INDICES[INDICES.length - 1])
                throw new IllegalStateException("Missing selected render targets");
            result.put("renderTargetCount", inventory.renderTargetCount());
            savedBinding = boundary.textureBinding2D();
            for (int index : INDICES) {
                Target target = inventory.targets().get(index);
                if (target == null || target.declaredFormat() == null || target.declaredFormat().isBlank()
                        || target.width() <= 0 || target.height() <= 0)
                    throw new IllegalStateException("Missing selected target declaration");
                Map<String, Object> query = new LinkedHashMap<>();
                query.put("index", index);
                query.put("declaredFormat", target.declaredFormat());
                query.put("declaredWidth", target.width());
                query.put("declaredHeight", target.height());
                queries.add(query);
                query.put("main", observe(boundary, target.mainTexture()));
                query.put("alt", observe(boundary, target.altTexture()));
            }
            result.put("available", true);
        } catch (Exception | LinkageError error) {
            result.put("errorClass", errorClass(error));
        } finally {
            if (savedBinding != null) {
                try {
                    boundary.bindTexture2D(savedBinding);
                    result.put("bindingRestored", true);
                } catch (Exception | LinkageError error) {
                    result.put("available", false);
                    result.put("restoreErrorClass", errorClass(error));
                }
            }
        }
        return result;
    }

    private static Map<String, Object> observe(SystemBoundary boundary, int texture) throws Exception {
        if (texture <= 0 || !boundary.textureExists(texture)) throw new IllegalStateException("Missing existing texture ID");
        boundary.bindTexture2D(texture);
        TextureLevel level = boundary.textureLevel();
        if (level == null || level.actualFormat() <= 0 || level.width() <= 0 || level.height() <= 0)
            throw new IllegalStateException("Missing allocated texture storage");
        return Map.of("textureId", texture, "actualFormat", level.actualFormat(),
                "width", level.width(), "height", level.height());
    }

    private static String errorClass(Throwable error) {
        while (error instanceof InvocationTargetException reflected && reflected.getCause() != null)
            error = reflected.getCause();
        return error.getClass().getSimpleName();
    }

    /** Reflection avoids JavaGL/Iris compile-time dependencies. No creation or pixel writes. */
    private static final class ReflectedBoundary implements SystemBoundary {
        private static final int TEXTURE_2D = 0x0DE1, TEXTURE_BINDING_2D = 0x8069;

        public Inventory existingTargets() throws Exception {
            Class<?> iris = Class.forName("net.irisshaders.iris.Iris");
            Object manager = iris.getMethod("getPipelineManager").invoke(null);
            if (manager == null) throw new IllegalStateException("No pipeline manager");
            Object pipeline = manager.getClass().getMethod("getPipelineNullable").invoke(manager);
            Class<?> pipelineType = Class.forName("net.irisshaders.iris.pipeline.IrisRenderingPipeline");
            if (!pipelineType.isInstance(pipeline)) throw new IllegalStateException("No Iris rendering pipeline");
            Field field = pipelineType.getDeclaredField("renderTargets");
            field.setAccessible(true);
            Object renderTargets = field.get(pipeline);
            Class<?> targetsType = Class.forName("net.irisshaders.iris.targets.RenderTargets");
            Class<?> targetType = Class.forName("net.irisshaders.iris.targets.RenderTarget");
            int count = (Integer) targetsType.getMethod("getRenderTargetCount").invoke(renderTargets);
            Map<Integer, Target> targets = new LinkedHashMap<>();
            for (int index : INDICES) {
                if (index >= count) continue;
                // get() observes only. getOrCreate() is intentionally never used.
                Object target = targetsType.getMethod("get", int.class).invoke(renderTargets, index);
                if (target == null) continue;
                Object declaredFormat = targetType.getMethod("getInternalFormat").invoke(target);
                if (!(declaredFormat instanceof Enum<?> format)) throw new IllegalStateException("Missing declared format");
                targets.put(index, new Target(format.name(),
                        (Integer) targetType.getMethod("getMainTexture").invoke(target),
                        (Integer) targetType.getMethod("getAltTexture").invoke(target),
                        (Integer) targetType.getMethod("getWidth").invoke(target),
                        (Integer) targetType.getMethod("getHeight").invoke(target)));
            }
            return new Inventory(count, targets);
        }

        public int textureBinding2D() throws Exception {
            return (Integer) gl("glGetInteger", new Class<?>[]{int.class}, TEXTURE_BINDING_2D);
        }

        public boolean textureExists(int texture) throws Exception {
            return (Boolean) gl("glIsTexture", new Class<?>[]{int.class}, texture);
        }

        public void bindTexture2D(int texture) throws Exception {
            gl("glBindTexture", new Class<?>[]{int.class, int.class}, TEXTURE_2D, texture);
        }

        public TextureLevel textureLevel() throws Exception {
            return new TextureLevel(parameter(0x1003), parameter(0x1000), parameter(0x1001));
        }

        private static int parameter(int name) throws Exception {
            return (Integer) gl("glGetTexLevelParameteri", new Class<?>[]{int.class, int.class, int.class}, TEXTURE_2D, 0, name);
        }

        private static Object gl(String method, Class<?>[] arguments, Object... values) throws Exception {
            return Class.forName("org.lwjgl.opengl.GL11").getMethod(method, arguments).invoke(null, values);
        }
    }
}
