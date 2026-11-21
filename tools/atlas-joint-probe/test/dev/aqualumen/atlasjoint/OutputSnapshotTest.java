package dev.aqualumen.atlasjoint;
import java.util.*;
public final class OutputSnapshotTest {
    private static class Fake implements OutputSnapshot.Boundary {
        OutputSnapshot.State state=new OutputSnapshot.State(41,1029,31,8,7,6,5,4,3,1,1);
        int program=23,frame=100,fbo=53,texture=91,encoding=9729;boolean srgb=false,restore=true,throwRead=false;int reads;
        public OutputSnapshot.State state(){return state;}
        public int program(){return program;}
        public int frame(){return frame;}
        public int[] viewport(){return new int[]{0,0,1600,900};}
        public int drawFbo(){return fbo;}
        public int outputTexture(){return texture;}
        public int colorEncoding(){return encoding;}
        public boolean srgbEnabled(){return srgb;}
        public float[] read(int f,List<OutputSnapshot.Pixel> points){reads++;state=new OutputSnapshot.State(f,36064,0,4,0,0,0,0,0,0,0);if(throwRead)throw new IllegalStateException();return new float[]{.2f,.4f,.6f,1};}
        public void restore(OutputSnapshot.State saved){if(restore)state=saved;}
    }
    private static Map<String,Object> run(Fake f){return OutputSnapshot.capture(23,100,53,91,List.of(new OutputSnapshot.Pixel(678,540)),f);}
    private static void require(boolean b){if(!b)throw new AssertionError();}
    public static void main(String[] args) {
        Fake f=new Fake();require(Boolean.TRUE.equals(run(f).get("available")));require(f.reads==1);
        f=new Fake();f.program=24;require(Boolean.FALSE.equals(run(f).get("available"))&&f.reads==0);
        f=new Fake();f.frame=101;require(Boolean.FALSE.equals(run(f).get("available"))&&f.reads==0);
        f=new Fake();f.fbo=54;require(Boolean.FALSE.equals(run(f).get("available"))&&f.reads==0);
        f=new Fake();f.srgb=true;require(Boolean.FALSE.equals(run(f).get("available"))&&f.reads==0);
        f=new Fake();f.restore=false;require(Boolean.FALSE.equals(run(f).get("available")));
        f=new Fake();f.throwRead=true;Map<String,Object> r=run(f);require(Boolean.FALSE.equals(r.get("available"))&&Boolean.TRUE.equals(r.get("stateRestored")));
        System.out.println("PASS seven synthetic after-quad/state boundary cases; no GL executed");
    }
}
