package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import org.lwjgl.opengl.*;

public final class ReceiverLightingState {
    public record Texture(int unit, int texture, int sampler, int width, int height) { }
    private final ReceiverRadianceVolume.Epoch epoch;
    private final int program;
    private final Map<String, float[]> values;
    private final Map<String, Texture> textures;

    private ReceiverLightingState(ReceiverRadianceVolume.Epoch epoch, int program,
                                  Map<String, float[]> values, Map<String, Texture> textures) {
        this.epoch = epoch;
        this.program = program;
        this.values = Map.copyOf(values);
        this.textures = Map.copyOf(textures);
    }

    public static ReceiverLightingState capture(ReceiverRadianceVolume.Epoch epoch) {
        try {
            if (!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
                throw new IllegalStateException("Receiver lighting capture outside render thread");
        } catch (ReflectiveOperationException error) {
            throw new IllegalStateException("Render thread boundary unavailable", error);
        }
        return capture(epoch, () -> { });
    }

    static ReceiverLightingState capture(ReceiverRadianceVolume.Epoch epoch, Runnable guard) {
        Objects.requireNonNull(epoch); Objects.requireNonNull(guard).run();
        int program = GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if (program == 0 || !GL20.glIsProgram(program) || GL20.glGetProgrami(program, GL20.GL_LINK_STATUS) == 0)
            throw new IllegalStateException("No linked receiver lighting owner");
        var types = new LinkedHashMap<String, Integer>();
        var size = ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
        var type = ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder()).asIntBuffer();
        for (int index = 0; index < GL20.glGetProgrami(program, GL20.GL_ACTIVE_UNIFORMS); index++) {
            String name = GL20.glGetActiveUniform(program, index, size, type);
            if (size.get(0) == 1) types.put(name, type.get(0));
        }
        String[] names = {"gbufferModelViewInverse", "shadowModelView", "shadowProjection", "cameraPosition",
                          "sunPosition", "shadowLightPosition", "frameTimeCounter", "rainStrength"};
        var values = new LinkedHashMap<String, float[]>();
        for (int index = 0; index < names.length; index++) {
            int length = index < 3 ? 16 : index < 6 ? 3 : 1;
            int expected = length == 16 ? GL20.GL_FLOAT_MAT4 : length == 3 ? GL20.GL_FLOAT_VEC3 : GL11.GL_FLOAT;
            requireType(types, names[index], expected);
            float[] data = new float[length];
            GL20.glGetUniformfv(program, GL20.glGetUniformLocation(program, names[index]), data);
            for (float value : data) if (!Float.isFinite(value)) throw new IllegalStateException("Nonfinite lighting uniform");
            values.put(names[index], data);
        }
        requireType(types, "aqualumenDimension", GL11.GL_INT);
        if (GL20.glGetUniformi(program, GL20.glGetUniformLocation(program, "aqualumenDimension")) != 0 ||
                values.get("rainStrength")[0] < 0 || values.get("rainStrength")[0] > 1 || values.get("frameTimeCounter")[0] < 0)
            throw new IllegalStateException("Unsupported receiver lighting environment");
        for (String name : new String[]{"sunPosition", "shadowLightPosition"}) {
            float[] vector = values.get(name);
            if (vector[0] == 0 && vector[1] == 0 && vector[2] == 0) throw new IllegalStateException("Undefined light direction");
        }
        var textures = new LinkedHashMap<String, Texture>();
        int active = GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for (String name : new String[]{"colortex6", "colortex7", "shadowtex0"}) {
                requireType(types, name, name.equals("shadowtex0") ? GL20.GL_SAMPLER_2D_SHADOW : GL20.GL_SAMPLER_2D);
                int unit = GL20.glGetUniformi(program, GL20.glGetUniformLocation(program, name));
                if (unit < 0 || unit >= GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS))
                    throw new IllegalStateException("Lighting sampler unit invalid");
                GL13.glActiveTexture(GL13.GL_TEXTURE0 + unit);
                int texture = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
                if (texture == 0 || !GL11.glIsTexture(texture)) throw new IllegalStateException("Lighting texture unavailable");
                int width = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_WIDTH);
                int height = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_HEIGHT);
                int sampler = GL.getCapabilities().OpenGL33 || GL.getCapabilities().GL_ARB_sampler_objects
                        ? GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING, unit) : 0;
                int compare = sampler == 0 ? GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D, GL14.GL_TEXTURE_COMPARE_MODE)
                        : GL33.glGetSamplerParameteri(sampler, GL14.GL_TEXTURE_COMPARE_MODE);
                boolean shadow = name.equals("shadowtex0");
                int format = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_INTERNAL_FORMAT);
                boolean depth = format == GL11.GL_DEPTH_COMPONENT || format == GL14.GL_DEPTH_COMPONENT16 || format == GL14.GL_DEPTH_COMPONENT24 ||
                        format == GL14.GL_DEPTH_COMPONENT32 || format == GL30.GL_DEPTH_COMPONENT32F ||
                        format == GL30.GL_DEPTH24_STENCIL8 || format == GL30.GL_DEPTH32F_STENCIL8;
                if (width < 1 || height < 1 || (shadow && (!depth || compare != GL30.GL_COMPARE_REF_TO_TEXTURE)) ||
                        (!shadow && compare != GL11.GL_NONE))
                    throw new IllegalStateException("Lighting texture storage/comparison unavailable: " + name +
                            " texture=" + texture + " sampler=" + sampler + " size=" + width + "x" + height +
                            " format=" + format + " compare=" + compare);
                textures.put(name, new Texture(unit, texture, sampler, width, height));
            }
        } finally { GL13.glActiveTexture(active); }
        Texture sky = textures.get("colortex6"), clear = textures.get("colortex7"), shadow = textures.get("shadowtex0");
        if (sky.height() < 3 || sky.width() != clear.width() || sky.height() != clear.height() ||
                sky.texture() == clear.texture() || sky.texture() == shadow.texture() || clear.texture() == shadow.texture())
            throw new IllegalStateException("Lighting caches are not distinct coherent resources");
        return new ReceiverLightingState(epoch, program, values, textures);
    }

    private static void requireType(Map<String, Integer> types, String name, int expected) {
        if (!Objects.equals(types.get(name), expected)) throw new IllegalStateException("Lighting uniform unavailable or mistyped: " + name);
    }

    public boolean current(ReceiverRadianceVolume.Epoch now) {
        return now != null && current(now.world(),now.frame(),now.resources());
    }
    public boolean current(Object world,long frame,long resources) {
        return epoch.matches(world,frame,resources);
    }
    public int program() { return program; }
    public float[] value(String name) { return Objects.requireNonNull(values.get(name)).clone(); }
    public Texture texture(String name) { return Objects.requireNonNull(textures.get(name)); }
}
