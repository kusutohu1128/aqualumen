package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;
import org.lwjgl.opengl.GL14;
import org.lwjgl.opengl.GL15;
import org.lwjgl.opengl.GL21;
import org.lwjgl.opengl.GL33;
import org.lwjgl.system.MemoryUtil;

public final class ReceiverAtlasReadback {
    public record Image(ReceiverAtlasAlpha alpha, int minFilter, int magFilter, int wrapU, int wrapV) {}
    private ReceiverAtlasReadback() {}

    public static Image capture(int texture, int sampler) {
        if (texture == 0 || !GL11.glIsTexture(texture) || sampler != 0 && !GL33.glIsSampler(sampler))
            throw new IllegalArgumentException("Owned atlas texture/sampler unavailable");
        int previousTexture = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
        int previousPack = GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING);
        int[] names = {GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_ROWS,
                GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SWAP_BYTES,GL12.GL_PACK_IMAGE_HEIGHT,GL12.GL_PACK_SKIP_IMAGES};
        int[] values = new int[names.length];
        for (int index = 0; index < names.length; index++) values[index] = GL11.glGetInteger(names[index]);
        ByteBuffer pixels = null;
        try {
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
            int width = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH);
            int height = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT);
            int format = GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_INTERNAL_FORMAT);
            int base = GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_BASE_LEVEL);
            int swizzle = GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL33.GL_TEXTURE_SWIZZLE_A);
            int compare = parameter(sampler,GL14.GL_TEXTURE_COMPARE_MODE);
            if (width < 1 || height < 1 || (long)width*height > 16777216
                    || base != 0 || swizzle != GL11.GL_ALPHA
                    || format != GL11.GL_RGBA8 && format != GL21.GL_SRGB8_ALPHA8 && format != GL11.GL_RGBA
                    || compare != GL11.GL_NONE)
                throw new IllegalStateException("Unsupported atlas alpha storage size="+width+"x"+height+
                        " format="+format+" base="+base+" swizzle="+swizzle+" compare="+compare);
            int min = parameter(sampler,GL11.GL_TEXTURE_MIN_FILTER), mag = parameter(sampler,GL11.GL_TEXTURE_MAG_FILTER);
            int wrapU = parameter(sampler,GL11.GL_TEXTURE_WRAP_S), wrapV = parameter(sampler,GL11.GL_TEXTURE_WRAP_T);
            pixels = MemoryUtil.memAlloc(Math.multiplyExact(Math.multiplyExact(width,height),4));
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,0);
            for (int name : names) GL11.glPixelStorei(name,name == GL11.GL_PACK_ALIGNMENT ? 1 : 0);
            GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,pixels);
            if (GL11.glGetError() != GL11.GL_NO_ERROR) throw new IllegalStateException("Atlas alpha readback GL error");
            byte[] alpha = new byte[width*height];
            for (int index = 0; index < alpha.length; index++) alpha[index] = pixels.get(index*4+3);
            return new Image(new ReceiverAtlasAlpha(width,height,alpha),min,mag,wrapU,wrapV);
        } finally {
            if (pixels != null) MemoryUtil.memFree(pixels);
            for (int index = 0; index < names.length; index++) GL11.glPixelStorei(names[index],values[index]);
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,previousPack);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,previousTexture);
        }
    }
    private static int parameter(int sampler, int name) {
        return sampler == 0 ? GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,name) : GL33.glGetSamplerParameteri(sampler,name);
    }
}
