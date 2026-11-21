package dev.aqualumen.bench;

import java.util.List;
import java.util.Map;
import java.lang.reflect.InvocationTargetException;

/** Public behavior tests: fake only the external MC/filesystem/GL boundary. */
public final class BathymetrySnapshotTest {
    public static void main(String[] args) {
        capturesExistingNamedBindingAndColumnsWithoutChangingCallerState();
        incompleteRestorationCannotReportSuccess();
        staleGlReadbackCannotStandInForCurrentUpload();
        outsideTestScopeIsInertBeforeAnyGlQueries();
        unknownProgramAndStaleSnapshotAreUnavailable();
        wrongBindingAndStorageAreNotAccepted();
        nonfiniteFieldIsNotHiddenByMatchingCpuData();
        failedReadbackStillRestoresAndRedacts();
        unknownZeroFieldIsAvailableButNotPositiveDepthEvidence();
        System.out.println("PASS bathymetry observer CPU existing-binding/column/state contract");
    }
    private static void outsideTestScopeIsInertBeforeAnyGlQueries() {
        for(int kind=0;kind<6;kind++) {
            Boundary boundary=new Boundary();boundary.scopeKind=kind;
            Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&!Boolean.TRUE.equals(result.get("scopeAuthorized")),"Invalid/unknown scope cannot authorize output");
            require(boundary.glQueries==0&&boundary.reads==0,"Disabled, ordinary, wrong UUID, LAN, multiple players and failed guards must be inert before GL");
        }
    }
    private static void unknownProgramAndStaleSnapshotAreUnavailable() {
        Boundary boundary=new Boundary();boundary.current=0;
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&"unknown_or_non_current_program".equals(result.get("reason"))&&boundary.reads==0,"Unknown actual program must be explicitly unavailable");
        boundary=new Boundary();boundary.snapshotFrame=39;
        result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&"mod_snapshot_unavailable_or_stale".equals(result.get("reason"))&&boundary.glQueries==0,"Old stored snapshots cannot authorize live GL observation");
    }
    private static void wrongBindingAndStorageAreNotAccepted() {
        for(int kind=0;kind<3;kind++) {
            Boundary boundary=new Boundary();boundary.storageKind=kind;
            Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))&&boundary.reads==0,"Wrong named binding, nonexistent texture and 16F storage must be unavailable without pixel reads");
        }
    }
    private static void nonfiniteFieldIsNotHiddenByMatchingCpuData() {
        Boundary boundary=new Boundary();boundary.nan=true;
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored")),"NaN must fail even if CPU and GL arrays match");
    }
    private static void failedReadbackStillRestoresAndRedacts() {
        Boundary boundary=new Boundary();boundary.readFailure=true;
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))&&boundary.pack==9,"Readback failure must restore active/pack state");
        require("IllegalArgumentException".equals(result.get("errorClass"))&&!result.toString().contains("secret-token"),"Only underlying class may be exported, never private error messages");
    }
    private static void unknownZeroFieldIsAvailableButNotPositiveDepthEvidence() {
        Boundary boundary=new Boundary();boundary.unknown=true;
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.TRUE.equals(result.get("available"))&&Integer.valueOf(0).equals(result.get("ready"))&&Integer.valueOf(0).equals(result.get("knownColumns")),"Bound zero field must report unknown, not fabricated positive water depth");
        require(Boolean.FALSE.equals(result.get("visualQualityAccepted"))&&Boolean.TRUE.equals(result.get("timingAcceptanceExcluded")),"Observation cannot accept visual quality or timing");
    }
    private static void staleGlReadbackCannotStandInForCurrentUpload() {
        Boundary boundary=new Boundary();boundary.stalePixels=true;
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored")),
                "Matching format/known counts are insufficient when actual GL pixels differ from current CPU upload");
    }
    private static void incompleteRestorationCannotReportSuccess() {
        Boundary boundary=new Boundary();boundary.ignoreRestore=true;
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("stateRestored")),
                "An omitted active/pack restore cannot be labeled restored or available");
    }
    private static void capturesExistingNamedBindingAndColumnsWithoutChangingCallerState() {
        Boundary boundary=new Boundary();
        Map<String,Object> result=BathymetrySnapshot.capture(101,boundary);
        require(Boolean.TRUE.equals(result.get("available")),"Existing named texture/uniforms must be observable");
        require(Boolean.TRUE.equals(result.get("stateRestored"))&&boundary.active==33987&&boundary.binding==77&&boundary.pack==9,
                "All caller texture/pack state must be restored");
        require(Integer.valueOf(101).equals(result.get("program"))&&Integer.valueOf(6).equals(result.get("samplerUnit")),"Record actual program and assigned unit");
        require(Integer.valueOf(201).equals(result.get("textureId"))&&Integer.valueOf(34836).equals(result.get("actualFormat")),"Actual binding/storage must not inherit a declaration");
        List<?> samples=(List<?>)result.get("samples");
        require(samples.size()==5,"Export exactly five bounded CPU-selected samples from one field readback");
        require(Double.valueOf(1.25).equals(((Map<?,?>)samples.get(0)).get("depth")),"Sample must come from the uploaded field, not a guessed floor");
        require(boundary.reads==1,"One complete bounded field readback, not per-frame sampling");
    }
    private static final class Boundary implements BathymetrySnapshot.SystemBoundary {
        int active=33987,binding=77,pack=9,reads;
        int scopeKind=-1,storageKind=-1,current=101,snapshotFrame=40,glQueries;
        boolean ignoreRestore,stalePixels,nan,readFailure,unknown;
        public BathymetrySnapshot.Scope scope() {
            if(scopeKind==5)throw new IllegalStateException("secret-token");
            return new BathymetrySnapshot.Scope(scopeKind!=0,true,scopeKind==3,scopeKind==4?2:1,true,
                    scopeKind==1?"ordinary":"AqualumenNaturalV2",scopeKind==2?"wrong":"b22dbccb-2970-41e6-847f-f183b1ec923d",308060,"minecraft:overworld",true,true);
        }
        public BathymetrySnapshot.ModState modState() {return new BathymetrySnapshot.ModState(201,snapshotFrame,unknown?0:1,unknown?0:4096,new float[]{-32.5f,-32.5f,64,-2},false,field());}
        public int frame() {return 40;}
        public int currentProgram() {glQueries++;return current;}
        public BathymetrySnapshot.Uniforms uniforms(int program) {glQueries++;return new BathymetrySnapshot.Uniforms(6,unknown?0:1,new float[]{-32.5f,-32.5f,64,-2});}
        public BathymetrySnapshot.State save() {return new BathymetrySnapshot.State(active,binding,pack,8,12,16,2,3,4,1,1);}
        public void selectUnit(int unit) {active=33984+unit;binding=201;}
        public BathymetrySnapshot.Texture texture() {return new BathymetrySnapshot.Texture(storageKind==0?202:binding,storageKind!=1,storageKind==2?34842:34836,64,64,9728,9728,33071,33071);}
        private float[] field() {float[] values=new float[64*64*4];if(!unknown)for(int i=0;i<values.length;i+=4){values[i]=1.25f;values[i+1]=-2;values[i+2]=1;}if(nan)values[0]=Float.NaN;return values;}
        public float[] readPixels() throws Exception {reads++;pack=0;if(readFailure)throw new InvocationTargetException(new IllegalArgumentException("secret-token"));float[] values=field();if(stalePixels)values[0]=1.5f;return values;}
        public void restore(BathymetrySnapshot.State state) {if(!ignoreRestore){active=state.active();binding=state.binding();pack=state.packBuffer();}}
    }
    private static void require(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
}
