package dev.aqualumen.stageprobe;

import dev.aqualumen.bench.BathymetrySnapshot;
import java.util.Map;
import java.util.Properties;

/** Synthetic CPU system-boundary data only; never actual GL observations. */
public final class StageSnapshotTest {
    private static void require(boolean value,String message) {
        if(!value)throw new AssertionError(message);
    }
    private static Properties configuration() {
        Properties p=new Properties();
        p.setProperty("schema","2");p.setProperty("world","AqualumenNaturalV2");
        p.setProperty("world_id","b22dbccb-2970-41e6-847f-f183b1ec923d");
        p.setProperty("expected_pack","Aqualumen-ShoreProbe-world-water-tessellation-test.zip");
        p.setProperty("expected_pack_sha256","a".repeat(64));return p;
    }
    private static BathymetrySnapshot.Scope scope(String world,boolean enabled) {
        return new BathymetrySnapshot.Scope(enabled,true,false,1,true,world,
                "b22dbccb-2970-41e6-847f-f183b1ec923d",308060,"minecraft:overworld",true,true);
    }
    private static StageSnapshot.Context context(String world,boolean enabled) {
        return new StageSnapshot.Context(configuration(),scope(world,enabled),true,42,false);
    }
    private static class MockBoundary implements StageSnapshot.Boundary {
        int glReads;
        public boolean usingTessellation(){return true;}
        public int frame(){return 100;}
        public int currentProgram(){glReads++;return 42;}
        public int programParameter(int p,int parameter){glReads++;return switch(parameter){case 35714->1;case 35717->4;case 36469->3;default->0;};}
        public int[] attachedShaders(int p,int maximum){glReads++;return new int[]{11,12,13,14};}
        public int shaderType(int shader){glReads++;return switch(shader){case 11->35633;case 12->36488;case 13->36487;case 14->35632;default->0;};}
        public String shaderSource(int shader,int maximum){glReads++;return "synthetic CPU source";}
        public int patchVertices(){glReads++;return 3;}
        public StageSnapshot.Capabilities capabilities(){glReads++;return new StageSnapshot.Capabilities("mock3.2","mock",true,false);}
    }
    private static void ordinaryWorldRejectsBeforeGl() {
        MockBoundary boundary=new MockBoundary();
        Map<String,Object> result=StageSnapshot.capture(context("ordinary-world",true),boundary);
        require(Boolean.FALSE.equals(result.get("available")),"Ordinary-world capture must be unavailable");
        require(boundary.glReads==0,"Ordinary world must perform zero external GL reads");
    }
    private static void linkedTerrainStagesAreExportedWithUnchangedProgramAndFrame() {
        Map<String,Object> result=StageSnapshot.capture(context("AqualumenNaturalV2",true),new MockBoundary());
        require(Boolean.TRUE.equals(result.get("available")),"Qualified synthetic linked terrain stages should be available");
        require(Boolean.TRUE.equals(result.get("programAndFrameUnchanged")),"Program/frame observation must be verified");
        require(result.get("tessControlOutputVertices").equals(3)&&result.get("patchVertices").equals(3),"Both patch arities must be exported");
        require(result.get("stages") instanceof java.util.List<?> stages&&stages.size()==4,"All four actual shader stages must be exported");
        require(Boolean.FALSE.equals(result.get("naturalVisualAccepted")),"Linked stages must not accept natural appearance");
    }
    private static void sourceObservationExportsHashesNotSourceText() {
        StageSnapshot.Context context=new StageSnapshot.Context(configuration(),scope("AqualumenNaturalV2",true),true,42,true);
        Map<String,Object> result=StageSnapshot.capture(context,new MockBoundary(){
            @Override public String shaderSource(int shader,int maximum){glReads++;return shader==13?"synthetic tessStageCoord = vec4(gl_TessCoord,1.0)":"synthetic CPU source";}
        });
        require(Boolean.TRUE.equals(result.get("available")),"Bounded optional actual-source observation should be available");
        require(Boolean.TRUE.equals(result.get("tesSourceMarkerPresent")),"TES-origin marker observation must be explicit");
        @SuppressWarnings("unchecked") java.util.List<Map<String,Object>> stages=(java.util.List<Map<String,Object>>)result.get("stages");
        require(stages.stream().allMatch(stage->String.valueOf(stage.get("sourceSha256")).matches("[0-9a-f]{64}")),"Every requested source needs a hash");
        require(!result.toString().contains("synthetic CPU source"),"Actual source text must not be exported");
    }
    private static void unavailableApiMustExportFailureWithoutPrivateMessage() {
        Map<String,Object> result=StageSnapshot.capture(context("AqualumenNaturalV2",true),new MockBoundary(){
            @Override public StageSnapshot.Capabilities capabilities(){throw new NoClassDefFoundError("private path must not escape");}
        });
        require(Boolean.FALSE.equals(result.get("available")),"Missing external API must be unavailable");
        require("NoClassDefFoundError".equals(result.get("errorClass")),"Only the exception class is exported");
        require(!result.toString().contains("private path"),"Private exception messages must not be exported");
    }
    private static void rejectedContextStaysPreGl() {
        MockBoundary disabled=new MockBoundary();
        require(Boolean.FALSE.equals(StageSnapshot.capture(context("AqualumenNaturalV2",false),disabled).get("available")),"Disabled marker scope is rejected");
        require(disabled.glReads==0,"Disabled marker must stay pre-GL");
        Properties wrongConfig=configuration();wrongConfig.setProperty("world_id","00000000-0000-0000-0000-000000000000");
        MockBoundary wrongWorld=new MockBoundary();
        require(Boolean.FALSE.equals(StageSnapshot.capture(new StageSnapshot.Context(wrongConfig,scope("AqualumenNaturalV2",true),true,42,false),wrongWorld).get("available")),"Wrong world UUID is rejected");
        require(wrongWorld.glReads==0,"Wrong world UUID must stay pre-GL");
        MockBoundary active=new MockBoundary();
        require(Boolean.FALSE.equals(StageSnapshot.capture(new StageSnapshot.Context(configuration(),scope("AqualumenNaturalV2",true),false,42,false),active).get("available")),"Active measurement is rejected");
        require(active.glReads==0,"Active measurement must stay pre-GL");
        MockBoundary noTess=new MockBoundary(){@Override public boolean usingTessellation(){return false;}};
        require(Boolean.FALSE.equals(StageSnapshot.capture(context("AqualumenNaturalV2",true),noTess).get("available")),"A solid non-tessellated pass is rejected");
        require(noTess.glReads==0,"Non-tessellated pass must stay pre-GL");
    }
    private static void incompleteOrChangedExternalObservationsAreUnavailable() {
        java.util.List<StageSnapshot.Boundary> invalid=java.util.List.of(
            new MockBoundary(){@Override public int shaderType(int id){return id==13?35632:super.shaderType(id);}},
            new MockBoundary(){@Override public int patchVertices(){return 4;}},
            new MockBoundary(){@Override public int programParameter(int p,int v){return v==36469?4:super.programParameter(p,v);}},
            new MockBoundary(){@Override public int programParameter(int p,int v){return v==35714?0:super.programParameter(p,v);}},
            new MockBoundary(){@Override public int programParameter(int p,int v){return v==35717?9:super.programParameter(p,v);}},
            new MockBoundary(){@Override public int[] attachedShaders(int p,int max){return new int[]{11,12,12,14};}},
            new MockBoundary(){private int next=42;@Override public int currentProgram(){return next++;}},
            new MockBoundary(){private int next=100;@Override public int frame(){return next++;}},
            new MockBoundary(){@Override public int currentProgram(){return 43;}},
            new MockBoundary(){@Override public StageSnapshot.Capabilities capabilities(){return new StageSnapshot.Capabilities("mock3.2","mock",false,false);}},
            new MockBoundary(){private boolean first=true;@Override public int currentProgram(){if(first){first=false;return 42;}throw new UnsatisfiedLinkError("secret");}}
        );
        for(StageSnapshot.Boundary boundary:invalid) {
            Map<String,Object> result=StageSnapshot.capture(context("AqualumenNaturalV2",true),boundary);
            require(Boolean.FALSE.equals(result.get("available")),"Incomplete, mismatched, changed or failed observation is rejected");
            require(!result.toString().contains("secret"),"Post-query errors must not expose messages");
        }
        StageSnapshot.Context sources=new StageSnapshot.Context(configuration(),scope("AqualumenNaturalV2",true),true,42,true);
        require(Boolean.FALSE.equals(StageSnapshot.capture(sources,new MockBoundary(){@Override public String shaderSource(int id,int max){return "x".repeat(262145);}}).get("available")),"Oversized source observation is rejected");
        require(Boolean.FALSE.equals(StageSnapshot.capture(sources,new MockBoundary(){@Override public String shaderSource(int id,int max){return null;}}).get("available")),"Missing requested source observation is rejected");
    }
    public static void main(String[] args) {
        ordinaryWorldRejectsBeforeGl();
        linkedTerrainStagesAreExportedWithUnchangedProgramAndFrame();
        sourceObservationExportsHashesNotSourceText();
        unavailableApiMustExportFailureWithoutPrivateMessage();
        rejectedContextStaysPreGl();
        incompleteOrChangedExternalObservationsAreUnavailable();
        System.out.println("PASS synthetic CPU: 21 stage cases, pre-GL scope/idle/tess guards, actual external stage/source observations, exception privacy and program/frame checks");
    }
}
