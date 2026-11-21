package dev.aqualumen.bench;

import java.io.BufferedWriter;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

final class GroundShadowClip implements AutoCloseable {
    static final int X = 780, Y = 490, WIDTH = 1024, HEIGHT = 480;
    private final int x, y, width, height;
    private final ByteBuffer pixels;
    private final Method read, get;
    private final FileChannel raw;
    private final BufferedWriter times;
    private long next;
    private int index;

    GroundShadowClip(Path dir) throws Exception {
        this(dir,X,Y,WIDTH,HEIGHT);
    }
    GroundShadowClip(Path dir,int x,int y,int width,int height) throws Exception {
        this.x=x; this.y=y; this.width=width; this.height=height;
        pixels=ByteBuffer.allocateDirect(Math.multiplyExact(Math.multiplyExact(width,height),4));
        read = Class.forName("org.lwjgl.opengl.GL45").getMethod("glGetTextureSubImage", int.class,int.class,
            int.class,int.class,int.class,int.class,int.class,int.class,int.class,int.class,ByteBuffer.class);
        get = Class.forName("org.lwjgl.opengl.GL11").getMethod("glGetInteger",int.class);
        Files.createDirectory(dir);
        times = Files.newBufferedWriter(dir.resolve("ticks.csv"), StandardOpenOption.CREATE_NEW);
        raw = FileChannel.open(dir.resolve("bottom-up.rgba"), StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        times.write("frame,elapsed_ns,world_tick\n");
    }
    void frame(long elapsed, long tick, int texture) throws Exception {
        if (elapsed < next || index >= 300) return;
        for (int state : new int[]{0x88ED,0x0D02,0x0D03,0x0D04,0x806B,0x806C}) {
            if ((int)get.invoke(null,state) != 0) throw new IllegalStateException("Non-default pixel pack address state");
        }
        pixels.clear();
        read.invoke(null,texture,0,x,y,0,width,height,1,0x1908,0x1401,pixels);
        while (pixels.hasRemaining()) raw.write(pixels);
        times.write(index + "," + elapsed + "," + tick + "\n");
        index++;
        next = (elapsed / 40_000_000L + 1) * 40_000_000L;
    }
    @Override public void close() throws java.io.IOException {
        try { raw.close(); } finally { times.close(); }
    }
}
