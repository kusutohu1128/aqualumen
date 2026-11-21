package dev.aqualumen.suntest;

import dev.aqualumen.bench.BathymetrySnapshot;
import java.util.Properties;

/** Explicit synthetic system-boundary fixture, not Minecraft execution. */
public final class SunAuthorizationTest {
    private static final String ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static Properties config() {
        Properties p=new Properties();p.setProperty("schema","2");p.setProperty("world","AqualumenNaturalV2");
        p.setProperty("world_id",ID);p.setProperty("expected_pack","Aqualumen-ShoreProbe-world-sun-test.zip");
        p.setProperty("expected_pack_sha256","a".repeat(64));return p;
    }
    private static BathymetrySnapshot.Scope accepted() {
        return new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",ID,308060,
            "minecraft:overworld",true,true);
    }
    private static class Fixture implements SunAuthorization.SystemBoundary {
        Properties configuration=config();BathymetrySnapshot.Scope current=accepted();boolean files=true;
        public SunAuthorization.Input input(){return new SunAuthorization.Input(files,configuration);}
        public BathymetrySnapshot.Scope scope(Properties ignored){return current;}
    }
    private static void expect(int expected,Fixture fixture,String name) {
        int actual=SunAuthorization.value(fixture);
        if(actual!=expected)throw new AssertionError(name+": expected "+expected+", got "+actual);
    }
    public static void main(String[] args) {
        expect(1,new Fixture(),"approved TEST scope supplies permission");
        Fixture absent=new Fixture();absent.files=false;expect(0,absent,"absent opt-in markers supply zero");
        Fixture invalidConfig=new Fixture();invalidConfig.configuration.setProperty("schema","1");
        expect(0,invalidConfig,"invalid benchmark config supplies zero");
        String[] names={"disabled scope","not integrated","LAN","two players","wrong camera","wrong world",
            "wrong UUID","wrong seed","wrong dimension","changed pack hash/reload","wrong physics"};
        for(int i=0;i<names.length;i++) {
            Fixture f=new Fixture();f.current=new BathymetrySnapshot.Scope(i!=0,i!=1,i==2,i==3?2:1,i!=4,
                i==5?"OrdinaryWorld":"AqualumenNaturalV2",i==6?"00000000-0000-0000-0000-000000000000":ID,
                i==7?1:308060,i==8?"minecraft:the_nether":"minecraft:overworld",i!=9,i!=10);
            expect(0,f,names[i]);System.out.println("PASS synthetic scope regression: "+names[i]);
        }
        for(String field:new String[]{"schema","world","world_id","expected_pack","expected_pack_sha256"}) {
            Fixture f=new Fixture();f.configuration.remove(field);expect(0,f,"missing "+field);
        }
        Fixture transition=new Fixture();var supplier=SunAuthorization.supplier(transition);
        if(supplier.getAsInt()!=1)throw new AssertionError("initial permitted supplier");
        transition.current=new BathymetrySnapshot.Scope(true,true,false,1,true,"OrdinaryWorld",ID,308060,
            "minecraft:overworld",true,true);
        if(supplier.getAsInt()!=0)throw new AssertionError("world transition must revoke without latch");
        transition.current=accepted();transition.current=new BathymetrySnapshot.Scope(true,true,false,1,true,
            "AqualumenNaturalV2",ID,308060,"minecraft:overworld",false,true);
        if(supplier.getAsInt()!=0)throw new AssertionError("pack reload mismatch must revoke without latch");
        transition.current=accepted();if(supplier.getAsInt()!=1)throw new AssertionError("fresh validated reload");
        if(SunAuthorization.value(null)!=0)throw new AssertionError("null boundary must reject");
        if(SunAuthorization.value(new Fixture(){public SunAuthorization.Input input(){throw new IllegalStateException();}})!=0)
            throw new AssertionError("boundary failure must reject");
        if(SunAuthorization.value(new Fixture(){public BathymetrySnapshot.Scope scope(Properties p){throw new LinkageError();}})!=0)
            throw new AssertionError("missing pinned API must reject");
        System.out.println("PASS synthetic CPU: markers/config, 11 live scope negatives, missing fields, exceptions, supplier transitions");
    }
}
