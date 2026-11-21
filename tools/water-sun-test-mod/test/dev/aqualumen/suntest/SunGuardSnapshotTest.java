package dev.aqualumen.suntest;

import dev.aqualumen.bench.BathymetrySnapshot;
import java.util.Properties;

/** Synthetic actual-API boundary values only; no live GL calls. */
public final class SunGuardSnapshotTest {
    private static SunAuthorization.SystemBoundary authorization() {
        return new SunAuthorization.SystemBoundary() {
            public SunAuthorization.Input input() {
                Properties p=new Properties();p.setProperty("schema","2");p.setProperty("world","AqualumenNaturalV2");
                p.setProperty("world_id","b22dbccb-2970-41e6-847f-f183b1ec923d");
                p.setProperty("expected_pack","Aqualumen-ShoreProbe-world-sun-test.zip");p.setProperty("expected_pack_sha256","a".repeat(64));
                return new SunAuthorization.Input(true,p);
            }
            public BathymetrySnapshot.Scope scope(Properties ignored) {
                return new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",
                    "b22dbccb-2970-41e6-847f-f183b1ec923d",308060,"minecraft:overworld",true,true);
            }
        };
    }
    private static class Fixture implements SunGuardSnapshot.SystemBoundary {
        public int frame(){return 123;}
        public int currentProgram(){return 425;}
        public SunGuardSnapshot.Uniform uniform(int p,String n){return new SunGuardSnapshot.Uniform(n,7,5124,1);}
        public int integerUniform(int p,int l){return 1;}
    }
    private static SunGuardSnapshot.Context context() {
        return new SunGuardSnapshot.Context(authorization(),"complete","TRANSLUCENT",true,true,425);
    }
    private static void reject(SunGuardSnapshot.Context c,SunGuardSnapshot.SystemBoundary b,String name) {
        if(Boolean.TRUE.equals(SunGuardSnapshot.capture(c,b).get("available")))throw new AssertionError(name);
    }
    public static void main(String[] args) {
        var observation=SunGuardSnapshot.capture(context(),new Fixture());
        if(!Boolean.TRUE.equals(observation.get("available")))throw new AssertionError("typed active int1 must be observed");
        for(SunGuardSnapshot.Uniform uniform:new SunGuardSnapshot.Uniform[]{null,
                new SunGuardSnapshot.Uniform("wrong",7,5124,1),new SunGuardSnapshot.Uniform("aqualumenSunTestAuthorized",-1,5124,1),
                new SunGuardSnapshot.Uniform("aqualumenSunTestAuthorized",7,5126,1),new SunGuardSnapshot.Uniform("aqualumenSunTestAuthorized",7,5124,2)})
            reject(context(),new Fixture(){public SunGuardSnapshot.Uniform uniform(int p,String n){return uniform;}},"inactive/wrong typed uniform");
        reject(context(),new Fixture(){public int integerUniform(int p,int l){return 0;}},"actual int0 rejected");
        reject(context(),new Fixture(){public int currentProgram(){return 426;}},"wrong current program rejected");
        reject(context(),new Fixture(){boolean changed;public int frame(){if(!changed){changed=true;return 123;}return 124;}},"frame change rejected");
        reject(context(),new Fixture(){boolean changed;public int currentProgram(){if(!changed){changed=true;return 425;}return 426;}},"program change rejected");
        reject(context(),new Fixture(){public int integerUniform(int p,int l){throw new IllegalStateException();}},"GL query failure rejected");
        SunGuardSnapshot.SystemBoundary forbidden=new Fixture(){public int frame(){throw new AssertionError("unsafe GL boundary reached");}};
        for(SunGuardSnapshot.Context c:new SunGuardSnapshot.Context[]{
                new SunGuardSnapshot.Context(null,"complete","TRANSLUCENT",true,true,425),
                new SunGuardSnapshot.Context(authorization(),"sampling","TRANSLUCENT",true,true,425),
                new SunGuardSnapshot.Context(authorization(),"complete","SOLID",true,true,425),
                new SunGuardSnapshot.Context(authorization(),"complete","TRANSLUCENT",false,true,425),
                new SunGuardSnapshot.Context(authorization(),"complete","TRANSLUCENT",true,false,425)})reject(c,forbidden,"unsafe scope/phase must reject before GL");
        System.out.println("PASS synthetic CPU: typed int1, inactive/type/size/value/program/frame/query negatives, unauthorized/active/solid/no-tess/pipeline pre-GL rejection");
    }
}
