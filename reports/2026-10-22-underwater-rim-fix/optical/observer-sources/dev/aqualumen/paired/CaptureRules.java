package dev.aqualumen.paired;

import java.nio.*;
import java.util.*;

/** Pure validation of the one-shot capture contract. */
public final class CaptureRules {
    public static final String WORLD_ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    public static final String PACK="Aqualumen-PairedWater-2026-10-22.zip";
    public record Request(String id,String scene,String runId,int width,int height) {}
    public record Identity(Object renderer,Object pipeline,Object targets,int program,int frame,
        int fbo,int output,int outputVersion,int width,int height,int c0,int c12,List<Double> camera) {}
    private CaptureRules() {}
    public static boolean configuration(Properties p) {
        return p!=null&&"2".equals(p.getProperty("schema"))&&"AqualumenNaturalV2".equals(p.getProperty("world"))
            &&WORLD_ID.equals(p.getProperty("world_id"))&&PACK.equals(p.getProperty("expected_pack"))
            &&p.getProperty("expected_pack_sha256","").matches("[0-9a-f]{64}");
    }
    public static Request request(Properties p) {
        String id=p.getProperty("request_id","");
        if(!UUID.fromString(id).toString().equals(id)||!WORLD_ID.equals(p.getProperty("world_id")))
            throw new IllegalArgumentException("request UUID/world");
        String scene=p.getProperty("scene","");
        if(!Set.of("underwater-up-near","underwater-up-deep").contains(scene))
            throw new IllegalArgumentException("fixed underwater scene required");
        String run=p.getProperty("recorder_run_id","");
        if(!run.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}"))throw new IllegalArgumentException("recorder run");
        int w=Integer.parseInt(p.getProperty("width","0")),h=Integer.parseInt(p.getProperty("height","0"));
        extent(w,h);return new Request(id,scene,run,w,h);
    }
    public static void extent(int w,int h) {
        if(w<1||h<1||w>2560||h>1440)throw new IllegalArgumentException("bounded viewport");
    }
    public static void same(Identity a,Identity b) {
        if(a==null||b==null||a.renderer()!=b.renderer()||a.pipeline()!=b.pipeline()||a.targets()!=b.targets()
            ||a.program()<=0||a.frame()<0||a.fbo()<=0||a.output()<=0||a.c0()<=0||a.c12()<=0
            ||a.c0()==a.c12()||a.output()==a.c0()||a.output()==a.c12()
            ||!a.equals(b))throw new IllegalStateException("FINAL invocation identity changed");
    }
    public static long[] diagnostics(FloatBuffer rgba,int width,int height) {
        extent(width,height);
        if(rgba==null||rgba.capacity()!=width*height*4)throw new IllegalArgumentException("partial diagnostic storage");
        long[] counts=new long[6];
        for(int i=0;i<rgba.capacity();i+=4) {
            float route=rgba.get(i),f=rgba.get(i+1),travel=rgba.get(i+2),mask=rgba.get(i+3);
            if(!Float.isFinite(route)||!Float.isFinite(f)||!Float.isFinite(travel)||!Float.isFinite(mask)
                ||route!=(int)route||route<0||route>5||f<0||f>1||travel<0
                ||(route==0?(f!=0||travel!=0||mask!=0):mask!=1))
                throw new IllegalStateException("nonfinite, partial, or invalid diagnostic record at "+i/4);
            counts[(int)route]++;
        }
        return counts;
    }
    public static byte[] rgba8(FloatBuffer rgba,int width,int height) {
        extent(width,height);
        if(rgba==null||rgba.capacity()!=width*height*4)throw new IllegalArgumentException("partial beauty storage");
        byte[] out=new byte[rgba.capacity()];
        for(int i=0;i<out.length;i++) {
            float v=rgba.get(i);int q=Math.round(v*255);
            if(!Float.isFinite(v)||v<0||v>1||Math.abs(v*255-q)>.001)
                throw new IllegalStateException("not a normalized RGBA8 read at "+i);
            out[i]=(byte)q;
        }
        return out;
    }
    public static byte[] littleEndian(FloatBuffer rgba) {
        ByteBuffer out=ByteBuffer.allocate(rgba.capacity()*4).order(ByteOrder.LITTLE_ENDIAN);
        for(int i=0;i<rgba.capacity();i++)out.putFloat(rgba.get(i));return out.array();
    }
}
