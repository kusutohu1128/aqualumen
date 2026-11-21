package dev.aqualumen.bench;

import dev.aqualumen.suntest.SunAuthorization;
import java.nio.file.Path;
import java.util.Properties;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Synthetic external Minecraft/time boundary; real frozen authorization code. */
public final class SunPerformanceTest {
    private static Properties config() {
        Properties p=new Properties();p.setProperty("schema","2");p.setProperty("world","AqualumenNaturalV2");
        p.setProperty("world_id","b22dbccb-2970-41e6-847f-f183b1ec923d");
        p.setProperty("expected_pack","Aqualumen-ShoreProbe-world-sun-test.zip");
        p.setProperty("expected_pack_sha256","a".repeat(64));return p;
    }
    private static final class Live implements SunAuthorization.SystemBoundary {
        boolean allowed=true;int reads;
        public SunAuthorization.Input input(){reads++;return new SunAuthorization.Input(true,config());}
        public BathymetrySnapshot.Scope scope(Properties p){return new BathymetrySnapshot.Scope(true,true,false,1,true,
            "AqualumenNaturalV2","b22dbccb-2970-41e6-847f-f183b1ec923d",308060,"minecraft:overworld",allowed,true);}
    }
    private static class Clock implements SunPerformance.Boundary {
        long tick;int frame=37;String phase="sampling";
        public long nanoTime(){tick+=100;return tick;}
        public int irisFrame(){return frame;}
        public String phase(){return phase;}
    }
    public static void main(String[] args) throws Exception {
        SunPerformance.begin("profile","tracer",Path.of(args[0]),new Clock());
        Live live=new Live();var supplier=SunPerformance.wrap(SunAuthorization.supplier(live));
        if(supplier.getAsInt()!=1||live.reads!=1)throw new AssertionError("wrapped live authorization changed");
        var report=SunPerformance.snapshot();
        if(!report.contains("\"supplierCalls\":1")||!report.contains("\"authorized\":1")
                ||!report.contains("\"frame\":37"))throw new AssertionError("one actual supplier event missing: "+report);
        System.out.println("PASS public tracer: real authorization return1, one fresh input read, one frame37 supplier event");
        live.allowed=false;if(supplier.getAsInt()!=0)throw new AssertionError("same-frame revocation lost");
        live.allowed=true;if(supplier.getAsInt()!=1)throw new AssertionError("fresh reauthorization lost");
        if(!SunPerformance.snapshot().contains("\"supplierCalls\":3")||live.reads!=3)
            throw new AssertionError("supplier cached result or event count");
        for(Clock broken:new Clock[]{new Clock(){public long nanoTime(){throw new IllegalStateException();}},
                new Clock(){public int irisFrame(){throw new LinkageError();}},
                new Clock(){public String phase(){throw new IllegalStateException();}}}){
            SunPerformance.begin("profile","failure",Path.of(args[0]),broken);
            if(supplier.getAsInt()!=1||!SunPerformance.snapshot().contains("\"metricsAvailable\":false"))
                throw new AssertionError("instrumentation failure changed original result");
        }
        SunPerformance.begin("profile","original-error",Path.of(args[0]),new Clock());
        AssertionError sentinel=new AssertionError("original");
        try{SunPerformance.wrap(()->{throw sentinel;}).getAsInt();throw new AssertionError("original error swallowed");}
        catch(AssertionError failure){if(failure!=sentinel)throw failure;}
        System.out.println("PASS fresh same-frame revocation and clock/frame/phase failure isolation; original Error identity propagates");
        Path scratch=Files.createTempDirectory(Path.of(args[0]),"profile-hash-test-");
        Path zip=scratch.resolve("fixture.zip");byte[] expected={1,2,3};Files.write(zip,expected);
        String pin=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(expected));
        SunPerformance.begin("profile","hash",scratch,new Clock());
        var hashSupplier=SunPerformance.wrap(()->{try{
            return SunPerformance.hash(()->HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(SunPerformance.bytes(Files.readAllBytes(zip)))).equals(pin))?1:0;
        }catch(Exception failure){return 0;}});
        if(hashSupplier.getAsInt()!=1)throw new AssertionError("hash result changed");
        var modified=expected.clone();modified[0]=9;Files.write(zip,modified);
        if(hashSupplier.getAsInt()!=0)throw new AssertionError("same-size changed ZIP reused success");
        if(!SunPerformance.snapshot().contains("\"hashCalls\":2")||!SunPerformance.snapshot().contains("\"hashBytes\":6"))
            throw new AssertionError("nested full-expression timing or bytes missing");
        System.out.println("PASS real temporary-file full hash preserved, same-size mutation revoked, nested bytes counted");
        SunPerformance.hash(()->true);
        if(!SunPerformance.snapshot().contains("\"hashCalls\":2")||!SunPerformance.snapshot().contains("\"unownedHashCalls\":1"))
            throw new AssertionError("observer-only hash attributed to supplier");
        Clock phases=new Clock();phases.phase="warmup";
        SunPerformance.begin("profile","phases",scratch,phases);
        var transitioning=SunPerformance.wrap(()->{phases.phase="sampling";return 1;});transitioning.getAsInt();
        phases.frame++;transitioning.getAsInt();
        if(!SunPerformance.snapshot().contains("\"phase\":\"warmup\"")||!SunPerformance.snapshot().contains("\"frame\":38"))
            throw new AssertionError("phase was inferred after delegate or frame invented");
        SunPerformance.begin("control","control",scratch,new Clock(){public long nanoTime(){throw new AssertionError("control clock");}
            public int irisFrame(){throw new AssertionError("control frame");}public String phase(){throw new AssertionError("control phase");}});
        if(supplier.getAsInt()!=1||!SunPerformance.hash(()->true)||!SunPerformance.snapshot().contains("\"supplierCalls\":null"))
            throw new AssertionError("control disabled original or measured counters");
        if(SunPerformance.finish("sampling","control",scratch)||Files.exists(scratch.resolve("sun-profile.json")))
            throw new AssertionError("exported during sampling");
        if(!SunPerformance.finish("complete","control",scratch)||SunPerformance.finish("complete","control",scratch))
            throw new AssertionError("completion export missing or repeated");
        if(!Files.readString(scratch.resolve("sun-profile.json")).contains("\"timingsMeasured\":false"))
            throw new AssertionError("control report mislabels timing");
        System.out.println("PASS unowned hash separation, entry-phase/frame grouping, counters-off control, completion-only immutable export");
        SunPerformance.begin("profile","end-clock",scratch,new Clock(){int n;public long nanoTime(){if(++n==2)throw new LinkageError();return n*100;}});
        if(supplier.getAsInt()!=1||!SunPerformance.snapshot().contains("\"metricsAvailable\":false"))
            throw new AssertionError("end-clock failure changed completed original result");
        Exception hashError=new Exception("original hash failure");
        SunPerformance.begin("profile","hash-error",scratch,new Clock());
        try{SunPerformance.hash(()->{throw hashError;});throw new AssertionError("hash error swallowed");}
        catch(Exception failure){if(failure!=hashError)throw failure;}
        if(SunPerformance.bytes(expected)!=expected)throw new AssertionError("bytes observer copied/replaced original");
        Clock bounded=new Clock();SunPerformance.begin("profile","bounds",scratch,bounded);
        int before=live.reads;
        for(int i=0;i<4097;i++){bounded.frame=i;if(supplier.getAsInt()!=1)throw new AssertionError("bounds changed permission");}
        if(live.reads-before!=4097||!SunPerformance.snapshot().contains("\"metricsAvailable\":false"))
            throw new AssertionError("bounded metrics did not preserve every fresh delegate");
        Path absent=scratch.resolve("not-created");SunPerformance.begin("profile","export-failure",absent,new Clock());
        if(supplier.getAsInt()!=1||SunPerformance.finish("complete","export-failure",absent)||supplier.getAsInt()!=1)
            throw new AssertionError("export failure changed authorization");
        System.out.println("PASS end-clock/hash-error/array identity, 4097 fresh checks past row bound, export failure isolation");
    }
}
