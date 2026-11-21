package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.opengl.GL;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;
import org.lwjgl.opengl.GL13;
import org.lwjgl.opengl.GL15;
import org.lwjgl.opengl.GL21;
import org.lwjgl.opengl.GL33;
import org.lwjgl.system.MemoryUtil;

public final class ReceiverAtlasReadbackGLTest {
    private static void check(boolean condition) {
        if (!condition) throw new AssertionError("Atlas GL readback contract failed");
    }
    public static void main(String[] arguments) {
        check(GLFW.glfwInit());
        GLFW.glfwWindowHint(GLFW.GLFW_VISIBLE,GLFW.GLFW_FALSE);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MAJOR,3);
        GLFW.glfwWindowHint(GLFW.GLFW_CONTEXT_VERSION_MINOR,3);
        long window = GLFW.glfwCreateWindow(16,16,"Atlas readback test",0,0);
        check(window != 0);
        GLFW.glfwMakeContextCurrent(window);
        GL.createCapabilities();
        System.out.println("Renderer: "+GL11.glGetString(GL11.GL_RENDERER));
        check(GL11.glGetString(GL11.GL_VENDOR).contains("NVIDIA"));
        int texture = GL11.glGenTextures(), other = GL11.glGenTextures(), sampler = GL33.glGenSamplers();
        int pack = GL15.glGenBuffers();
        ByteBuffer pixels = MemoryUtil.memAlloc(16);
        try {
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
            for (int index = 0; index < 4; index++) pixels.putInt(index*4,index == 0 || index == 3 ? 0 : -1);
            GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA8,2,2,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,pixels);
            GL33.glSamplerParameteri(sampler,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_LINEAR);
            GL33.glSamplerParameteri(sampler,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
            GL33.glSamplerParameteri(sampler,GL11.GL_TEXTURE_WRAP_S,GL12.GL_CLAMP_TO_EDGE);
            GL33.glSamplerParameteri(sampler,GL11.GL_TEXTURE_WRAP_T,GL11.GL_REPEAT);
            GL13.glActiveTexture(GL13.GL_TEXTURE0+3);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,other);
            GL15.glBindBuffer(GL21.GL_PIXEL_PACK_BUFFER,pack);
            GL15.glBufferData(GL21.GL_PIXEL_PACK_BUFFER,1,GL15.GL_STREAM_READ);
            int[] names = {GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_ROWS,
                    GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SWAP_BYTES,GL12.GL_PACK_IMAGE_HEIGHT,GL12.GL_PACK_SKIP_IMAGES};
            int[] values = {8,7,2,3,1,9,1};
            for (int index = 0; index < names.length; index++) GL11.glPixelStorei(names[index],values[index]);
            var image = ReceiverAtlasReadback.capture(texture,sampler);
            check(image.minFilter() == GL11.GL_LINEAR && image.magFilter() == GL11.GL_NEAREST);
            check(image.wrapU() == GL12.GL_CLAMP_TO_EDGE && image.wrapV() == GL11.GL_REPEAT);
            check(image.alpha().sampleBaseLevel(.25,.25,ReceiverAtlasAlpha.Filter.NEAREST,
                    ReceiverAtlasAlpha.Wrap.CLAMP,ReceiverAtlasAlpha.Wrap.CLAMP) == 0);
            check(image.alpha().sampleBaseLevel(.75,.25,ReceiverAtlasAlpha.Filter.NEAREST,
                    ReceiverAtlasAlpha.Wrap.CLAMP,ReceiverAtlasAlpha.Wrap.CLAMP) == 1);
            for (int format : new int[] {GL11.GL_RGBA,GL21.GL_SRGB8_ALPHA8}) {
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
                GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,format,2,2,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,pixels);
                System.out.println("Atlas format requested="+format+" observed="+
                        GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_INTERNAL_FORMAT));
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,other);
                var alternate = ReceiverAtlasReadback.capture(texture,sampler);
                check(alternate.alpha().sampleBaseLevel(.25,.25,ReceiverAtlasAlpha.Filter.NEAREST,
                        ReceiverAtlasAlpha.Wrap.CLAMP,ReceiverAtlasAlpha.Wrap.CLAMP) == 0);
                check(alternate.alpha().sampleBaseLevel(.75,.25,ReceiverAtlasAlpha.Filter.NEAREST,
                        ReceiverAtlasAlpha.Wrap.CLAMP,ReceiverAtlasAlpha.Wrap.CLAMP) == 1);
            }
            for (int attempt = 0; attempt < 3; attempt++) {
                check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE) == GL13.GL_TEXTURE0+3);
                check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D) == other);
                check(GL11.glGetInteger(GL21.GL_PIXEL_PACK_BUFFER_BINDING) == pack);
                for (int index = 0; index < names.length; index++) check(GL11.glGetInteger(names[index]) == values[index]);
                if (attempt == 0) {
                    GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
                    GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_BASE_LEVEL,1);
                    GL11.glBindTexture(GL11.GL_TEXTURE_2D,other);
                    try {
                        ReceiverAtlasReadback.capture(texture,sampler);
                        throw new AssertionError("Unsupported base level admitted");
                    } catch (IllegalStateException expected) {}
                } else if (attempt == 1) {
                    GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
                    GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL12.GL_TEXTURE_BASE_LEVEL,0);
                    GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL11.GL_RGB8,2,2,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,pixels);
                    GL11.glBindTexture(GL11.GL_TEXTURE_2D,other);
                    try {
                        ReceiverAtlasReadback.capture(texture,sampler);
                        throw new AssertionError("Alpha-less RGB admitted");
                    } catch (IllegalStateException expected) {}
                }
            }
            check(GL11.glGetError() == GL11.GL_NO_ERROR);
            System.out.println("PASS NVIDIA RGBA/RGBA8/SRGB8_ALPHA8 alpha readback, RGB rejection, sampler metadata, hostile pack/PBO restoration and failure restoration; not live plant sampling parity");
        } finally {
            MemoryUtil.memFree(pixels);
            GL15.glDeleteBuffers(pack); GL33.glDeleteSamplers(sampler);
            GL11.glDeleteTextures(texture); GL11.glDeleteTextures(other);
            GLFW.glfwDestroyWindow(window); GLFW.glfwTerminate();
        }
    }
}
