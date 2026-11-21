package dev.aqualumen.paired;

import java.io.ByteArrayInputStream;
import java.nio.*;
import java.util.*;
import javax.imageio.ImageIO;

public final class CaptureRulesTest {
    private static int assertions;
    private static void check(boolean ok){assertions++;if(!ok)throw new AssertionError();}
    private static void rejects(Runnable r){assertions++;try{r.run();throw new AssertionError("accepted invalid input");}catch(IllegalArgumentException|IllegalStateException expected){}}
    private static Properties properties() {
        Properties p=new Properties();p.setProperty("schema","2");p.setProperty("world","AqualumenNaturalV2");
        p.setProperty("world_id",CaptureRules.WORLD_ID);p.setProperty("expected_pack",CaptureRules.PACK);
        p.setProperty("expected_pack_sha256","a".repeat(64));p.setProperty("request_id","45b3a285-4887-47f3-ae44-ecad82a194f7");
        p.setProperty("scene","underwater-up-near");p.setProperty("recorder_run_id","test-near");p.setProperty("width","2");p.setProperty("height","3");return p;
    }
    private static CaptureRules.Identity identity(Object renderer,int frame,List<Double> camera) {
        return new CaptureRules.Identity(renderer,renderer,renderer,2,frame,3,4,1,2,3,5,6,camera);
    }
    public static void main(String[] args)throws Exception {
        Properties p=properties();check(CaptureRules.configuration(p));check(CaptureRules.request(p).height()==3);
        for(String field:List.of("schema","world","world_id","expected_pack","expected_pack_sha256")) {
            Properties broken=(Properties)p.clone();broken.setProperty(field,"other");check(!CaptureRules.configuration(broken));
        }
        for(String field:List.of("request_id","world_id","scene","recorder_run_id","width","height")) {
            Properties broken=(Properties)p.clone();broken.setProperty(field,field.equals("width")?"2561":field.equals("height")?"1441":"!");
            rejects(()->CaptureRules.request(broken));
        }
        Object renderer=new Object();List<Double> camera=List.of(1.0,2.0,3.0);
        CaptureRules.Identity a=identity(renderer,42,camera);CaptureRules.same(a,a);
        rejects(()->CaptureRules.same(a,identity(new Object(),42,camera)));
        rejects(()->CaptureRules.same(a,identity(renderer,43,camera)));
        rejects(()->CaptureRules.same(a,identity(renderer,42,List.of(1.0,2.0,3.1))));
        List<CaptureRules.Identity> drifts=List.of(
            new CaptureRules.Identity(renderer,new Object(),renderer,2,42,3,4,1,2,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,new Object(),2,42,3,4,1,2,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,7,42,3,4,1,2,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,2,42,7,4,1,2,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,2,42,3,7,1,2,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,2,42,3,4,2,2,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,2,42,3,4,1,3,3,5,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,2,42,3,4,1,2,3,7,6,camera),
            new CaptureRules.Identity(renderer,renderer,renderer,2,42,3,4,1,2,3,5,7,camera));
        for(var drift:drifts)rejects(()->CaptureRules.same(a,drift));
        float[] all={0,0,0,0,1,.5f,2,1,2,1,3,1,3,0,4,1,4,.2f,0,1,5,.3f,0,1};
        check(Arrays.equals(CaptureRules.diagnostics(FloatBuffer.wrap(all),2,3),new long[]{1,1,1,1,1,1}));
        for(float bad:new float[]{Float.NaN,Float.POSITIVE_INFINITY,-1,6,2.5f}) {
            float[] data=all.clone();data[4]=bad;rejects(()->CaptureRules.diagnostics(FloatBuffer.wrap(data),2,3));
        }
        for(int channel:new int[]{0,1,2,3,5,6,7}) {
            float[] data=all.clone();data[channel]=channel==6?-1:channel==5?1.1f:channel==7?0:1;
            rejects(()->CaptureRules.diagnostics(FloatBuffer.wrap(data),2,3));
        }
        rejects(()->CaptureRules.diagnostics(FloatBuffer.wrap(new float[20]),2,3));
        check(Arrays.equals(CaptureRules.littleEndian(FloatBuffer.wrap(new float[]{1})),new byte[]{0,0,(byte)128,63}));
        float[] beauty={1,0,0,1,0,1,0,1,0,0,1,1,1,1,1,1};
        byte[] raw=CaptureRules.rgba8(FloatBuffer.wrap(beauty),2,2);
        var image=ImageIO.read(new ByteArrayInputStream(PairedObserver.png(raw,2,2)));
        check(image.getRGB(0,0)==0xff0000ff);check(image.getRGB(1,0)==0xffffffff);
        check(image.getRGB(0,1)==0xffff0000);check(image.getRGB(1,1)==0xff00ff00);
        for(float bad:new float[]{Float.NaN,Float.NEGATIVE_INFINITY,-.1f,1.1f,.123f}) {
            float[] data=beauty.clone();data[0]=bad;rejects(()->CaptureRules.rgba8(FloatBuffer.wrap(data),2,2));
        }
        List<Integer> pack=List.of(8,7,6,5,4,3,1,1);
        GlReadback.State original=new GlReadback.State(33987,22,31,36065,11,pack);
        class Fake implements GlReadback.Boundary {
            GlReadback.State value=original;boolean sabotage;
            public GlReadback.State state(){return value;}
            public void restore(GlReadback.State s){if(!sabotage)value=s;}
        }
        Fake b=new Fake();
        check(GlReadback.preserving(b,()->{b.value=new GlReadback.State(1,2,3,4,5,List.of());return 123;})==123);
        check(b.state().equals(original));
        try{GlReadback.preserving(b,()->{b.value=new GlReadback.State(1,2,3,4,5,List.of());throw new IllegalStateException("read failed");});throw new AssertionError();}
        catch(IllegalStateException expected){check(b.state().equals(original));}
        b.sabotage=true;
        try{GlReadback.preserving(b,()->{b.value=new GlReadback.State(1,2,3,4,5,List.of());return null;});throw new AssertionError();}
        catch(IllegalStateException expected){check(expected.getMessage().contains("restoration"));}
        System.out.println("PASS paired capture CPU guards, route validation, GL state-boundary success/failure, asymmetric pixel orientation; assertions="+assertions);
    }
}
