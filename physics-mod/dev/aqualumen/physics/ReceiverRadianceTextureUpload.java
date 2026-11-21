package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import org.lwjgl.opengl.*;

public final class ReceiverRadianceTextureUpload implements ReceiverRadiancePublisher.Upload {
    private final Runnable threadGuard;
    private final int maximumPixels;

    public ReceiverRadianceTextureUpload() { this(ReceiverRadianceTextureUpload::renderThread); }
    ReceiverRadianceTextureUpload(Runnable threadGuard) { this(threadGuard,65536); }
    ReceiverRadianceTextureUpload(Runnable threadGuard,int maximumPixels) {
        this.threadGuard = java.util.Objects.requireNonNull(threadGuard);
        if(maximumPixels<1 || maximumPixels>1048576)throw new IllegalArgumentException("Unbounded receiver upload policy");
        this.maximumPixels=maximumPixels;
    }
    public static ReceiverRadianceTextureUpload plants() {
        return new ReceiverRadianceTextureUpload(ReceiverRadianceTextureUpload::renderThread,1048576);
    }
    private static void renderThread() {
        try {
            if (!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
                throw new IllegalStateException("Receiver upload outside render thread");
        } catch (ReflectiveOperationException error) { throw new IllegalStateException("Render thread boundary unavailable", error); }
    }

    @Override public int create(int width, int height, float[] values) {
        threadGuard.run();
        int maximumDimension=maximumPixels>65536?16384:4096;
        if (width < 1 || width > maximumDimension || height < 1 || height > maximumDimension || (long)width * height > maximumPixels ||
                values == null || values.length != width * height * 4) throw new IllegalArgumentException("Receiver upload extent invalid");
        if(width>GL11.glGetInteger(GL11.GL_MAX_TEXTURE_SIZE) || height>GL11.glGetInteger(GL11.GL_MAX_TEXTURE_SIZE))
            throw new IllegalArgumentException("Receiver upload exceeds device texture extent");
        for (float value : values) if (!Float.isFinite(value)) throw new IllegalArgumentException("Nonfinite receiver texture");
        var pixels = ByteBuffer.allocateDirect(values.length * Float.BYTES).order(ByteOrder.nativeOrder()).asFloatBuffer();
        pixels.put(values).flip();
        int active = GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        int binding = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
        int unpack = GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING);
        int[] names = {GL11.GL_UNPACK_ALIGNMENT, GL11.GL_UNPACK_ROW_LENGTH, GL11.GL_UNPACK_SKIP_ROWS,
                       GL11.GL_UNPACK_SKIP_PIXELS, GL11.GL_UNPACK_SWAP_BYTES};
        int[] previous = new int[names.length];
        for (int index = 0; index < names.length; index++) previous[index] = GL11.glGetInteger(names[index]);
        int texture = 0;
        try {
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER, 0);
            for (int name : names) GL11.glPixelStorei(name, name == GL11.GL_UNPACK_ALIGNMENT ? 4 : 0);
            texture = GL11.glGenTextures();
            if (texture <= 0) throw new IllegalStateException("Receiver texture name allocation failed");
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, texture);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL12.GL_CLAMP_TO_EDGE);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL12.GL_CLAMP_TO_EDGE);
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL30.GL_RGBA32F, width, height, 0, GL11.GL_RGBA, GL11.GL_FLOAT, pixels);
            if (GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_WIDTH) != width ||
                    GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_HEIGHT) != height ||
                    GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D, 0, GL11.GL_TEXTURE_INTERNAL_FORMAT) != GL30.GL_RGBA32F)
                throw new IllegalStateException("Receiver texture storage allocation failed");
            return texture;
        } catch (RuntimeException error) {
            if (texture != 0) GL11.glDeleteTextures(texture);
            throw error;
        } finally {
            GL13.glActiveTexture(active); GL11.glBindTexture(GL11.GL_TEXTURE_2D, binding);
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER, unpack);
            for (int index = 0; index < names.length; index++) GL11.glPixelStorei(names[index], previous[index]);
        }
    }

    @Override public void delete(int texture) {
        threadGuard.run();
        if (texture > 0) GL11.glDeleteTextures(texture);
    }
}
