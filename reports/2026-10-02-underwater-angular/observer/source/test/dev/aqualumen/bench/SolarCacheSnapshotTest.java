package dev.aqualumen.bench;

import java.util.List;
import java.util.Map;
import java.lang.reflect.InvocationTargetException;

/** Public source observations and externally visible GL state only; CPU-only. */
public final class SolarCacheSnapshotTest {
    public static void main(String[] args) {
        capturesActualWaterProjectionWithoutChangingCaller();
        unverifiableProjectionStateCannotBeAvailable();
        failedOuterCaptureCannotExposeAcceptedProjection();
        missingOrIncompatibleProjectionCannotBeSilentlyAccepted();
        invalidProjectionContextCannotBecomeSceneEvidence();
        legacyCacheOnlyAndFailedCacheDoNotRequireMatrices();
        observesNamedCurrentCacheAndRestoresCaller();
        changedNamedAssignmentCannotBecomeConnectionEvidence();
        unauthorizedAndTimedContextsNeverReachGl();
        unknownProgramAndInactiveSamplerAreUnavailable();
        wrongBindingsAndStorageAreUnavailable();
        invalidOrFailedReadbackRestoresStateAndRedactsMessages();
        incompleteOrThrowingRestoreCannotClaimSuccess();
        System.out.println("PASS solar cache and actual typed water-projection CPU observations; actual Iris projection remains untested");
    }
    private static void failedOuterCaptureCannotExposeAcceptedProjection() {
        Boundary boundary=new Boundary();boundary.throwOnRestore=true;
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
        Map<?,?> projection=(Map<?,?>)result.get("projection");
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("stateRestored"))
                &&Boolean.FALSE.equals(projection.get("available")),"An unsuccessful outer capture cannot leave accepted projection evidence");
        require("outer_capture_failed".equals(projection.get("reason")),"Projection export explicitly identifies outer-contract failure");
    }
    private static void missingOrIncompatibleProjectionCannotBeSilentlyAccepted() {
        for(ShoreSamplerSnapshot.Uniform value:new ShoreSamplerSnapshot.Uniform[]{null,
                new ShoreSamplerSnapshot.Uniform(-1,0x8B5C,1,-1,new float[16]),
                new ShoreSamplerSnapshot.Uniform(20,0x8B51,1,-1,new float[16]),
                new ShoreSamplerSnapshot.Uniform(20,0x8B5C,2,-1,new float[16]),
                new ShoreSamplerSnapshot.Uniform(20,0x8B5C,1,-1,new float[15]),
                new ShoreSamplerSnapshot.Uniform(20,0x8B5C,1,-1,new float[]{Float.NaN,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1})}) {
            Boundary boundary=new Boundary();boundary.replaceUniform="gbufferProjectionInverse";boundary.replacementUniform=value;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(((Map<?,?>)result.get("projection")).get("available"))
                    &&Boolean.TRUE.equals(result.get("stateRestored")),"Missing/inactive/wrong-type/non-scalar/incomplete/nonfinite actual inverse is failure, not a CPU substitute");
        }
        for(String name:new String[]{"isEyeInWater","viewWidth","viewHeight"}) {
            Boundary boundary=new Boundary();boundary.replaceUniform=name;
            boundary.replacementUniform=new ShoreSamplerSnapshot.Uniform(30,0x8B51,1,-1,new float[]{1});
            require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary).get("available")),
                    "Actual eye/source dimensions require their declared scalar types");
        }
    }
    private static void invalidProjectionContextCannotBecomeSceneEvidence() {
        for(int[] viewport:new int[][]{null,{0,0,1600},{1,0,1600,900},{0,0,1601,900},{0,0,1600,0},{0,0,2561,1440}}) {
            Boundary boundary=new Boundary();boundary.replaceViewport=true;boundary.replacementViewport=viewport;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored")),
                    "Actual viewport must be bounded and match actual shader source dimensions");
        }
        Boundary boundary=new Boundary();
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TERRAIN",true,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&"projection_requires_translucent_water_program".equals(((Map<?,?>)result.get("projection")).get("reason")),
                "Terrain program matrices cannot replace identified water-program matrices");
        for(int changed=0;changed<3;changed++) {
            boundary=new Boundary();boundary.projectionMutation=changed;
            result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(((Map<?,?>)result.get("projection")).get("available"))
                    &&Boolean.TRUE.equals(result.get("stateRestored")),"Changed program/frame/caller state invalidates the projection and restores the original caller");
        }
    }
    private static void legacyCacheOnlyAndFailedCacheDoNotRequireMatrices() {
        Boundary boundary=new Boundary();boundary.projectionQueriesAllowed=false;
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
        Map<?,?> projection=(Map<?,?>)result.get("projection");
        require(Boolean.TRUE.equals(result.get("available"))&&Boolean.FALSE.equals(projection.get("requested"))
                &&Boolean.FALSE.equals(projection.get("available"))&&"not_requested".equals(projection.get("reason")),
                "Legacy C7-only observation remains explicit and independent of projection support");
        boundary=new Boundary();boundary.projectionQueriesAllowed=false;boundary.pixels[0]=0;
        result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&"cache_capture_not_successful".equals(((Map<?,?>)result.get("projection")).get("reason")),
                "Failed C7 proof never attempts projection queries");
    }
    private static void unverifiableProjectionStateCannotBeAvailable() {
        Boundary boundary=new Boundary();boundary.failProjectionStateQuery=true;
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
        Map<?,?> projection=(Map<?,?>)result.get("projection");
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(projection.get("available"))
                &&Boolean.FALSE.equals(projection.get("stateUnchanged")),"Unverified matrix-query state cannot claim available projection");
        require(Boolean.TRUE.equals(result.get("stateRestored")),"A failed projection query still restores the outer cache caller");
    }
    private static void capturesActualWaterProjectionWithoutChangingCaller() {
        Boundary boundary=new Boundary();
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary);
        require(Boolean.TRUE.equals(result.get("available")),"Requested actual water projection must be available");
        Map<?,?> projection=result.get("projection") instanceof Map<?,?> value?value:Map.of();
        require(Boolean.TRUE.equals(projection.get("available")),"Actual uploaded water matrices must be exported, not a guessed FOV");
        Map<?,?> matrices=(Map<?,?>)projection.get("matrices");
        for(String name:Boundary.MATRIX_NAMES) {
            Map<?,?> matrix=(Map<?,?>)matrices.get(name);
            ShoreSamplerSnapshot.Uniform actual=boundary.uniform(201,name);
            require(Integer.valueOf(actual.location()).equals(matrix.get("location"))
                    &&Integer.valueOf(0x8B5C).equals(matrix.get("type"))&&Integer.valueOf(1).equals(matrix.get("size")),
                    "Only the actual named scalar mat4 qualifies");
            List<?> values=(List<?>)matrix.get("values");
            require(values.size()==16,"Matrix export has exactly sixteen column-major values");
            for(int i=0;i<16;i++)require(Double.valueOf(actual.values()[i]).equals(values.get(i)),
                    "Every uploaded float value must survive export without recomputing inverses");
        }
        require(List.of(0,0,1600,900).equals(projection.get("viewport")),"Export actual GL viewport, not screenshot-derived aspect");
        Map<?,?> scalars=(Map<?,?>)projection.get("scalars");
        require(Integer.valueOf(1).equals(((Map<?,?>)scalars.get("isEyeInWater")).get("value"))
                &&Double.valueOf(1600).equals(((Map<?,?>)scalars.get("viewWidth")).get("value"))
                &&Double.valueOf(900).equals(((Map<?,?>)scalars.get("viewHeight")).get("value")),
                "Export actual typed eye and source dimensions");
        require(Boolean.TRUE.equals(projection.get("stateUnchanged"))
                &&projection.get("stateBefore").equals(projection.get("stateAfter"))
                &&Boolean.TRUE.equals(result.get("stateRestored"))&&boundary.save().equals(boundary.original),
                "Matrix queries are caller-state neutral and the whole capture restores its original caller");
    }
    private static void unauthorizedAndTimedContextsNeverReachGl() {
        for(int variant=0;variant<11;variant++) {
            Boundary boundary=new Boundary();boundary.allowGl=false;
            boundary.scope=new BathymetrySnapshot.Scope(variant!=0,variant!=1,variant==2,variant==3?2:1,variant!=4,
                    variant==5?"ordinary":"AqualumenNaturalV2",variant==6?"00000000-0000-0000-0000-000000000000":"b22dbccb-2970-41e6-847f-f183b1ec923d",
                    variant==7?1:308060,variant==8?"minecraft:the_nether":"minecraft:overworld",variant!=9,variant!=10);
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("scopeAuthorized")),
                    "Every unapproved world/pack/Mod boundary stays inert");
            require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary).get("available")),
                    "Projection request cannot bypass any strict world/pack/Mod guard");
        }
        for(String phase:new String[]{"sampling","warmup","preparing","preparing-scene","screenshot","finishing","quitting","unknown"}) {
            Boundary boundary=new Boundary();boundary.phase=phase;boundary.allowGl=false;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&"measurement_or_lifecycle_active".equals(result.get("reason")),
                    "Active instrumentation never polls GL or enters timings");
            require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",true,boundary).get("available")),
                    "Projection requests also remain GL-inert during measurement");
        }
        Boundary boundary=new Boundary();boundary.pipelineCurrent=false;boundary.allowGl=false;
        require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TERRAIN",boundary).get("available")),
                "A stale pipeline cannot be observed");
        boundary=new Boundary();boundary.allowGl=false;
        require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"FINAL",boundary).get("available")),
                "An unused FINAL sampler cannot stand in for a terrain/water input");
    }
    private static void unknownProgramAndInactiveSamplerAreUnavailable() {
        for(int program:new int[]{0,202}) {
            Boundary boundary=new Boundary();boundary.program=program;
            require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary).get("available")),
                    "Only the identified current program can supply an observation");
        }
        for(SolarCacheSnapshot.Sampler sampler:new SolarCacheSnapshot.Sampler[]{null,
                new SolarCacheSnapshot.Sampler(-1,0x8B5E,1,5),new SolarCacheSnapshot.Sampler(7,0x1406,1,5),
                new SolarCacheSnapshot.Sampler(7,0x8B5E,2,5),new SolarCacheSnapshot.Sampler(7,0x8B5E,1,-1),
                new SolarCacheSnapshot.Sampler(7,0x8B5E,1,32),new SolarCacheSnapshot.Sampler(7,0x8B5E,1,0),
                new SolarCacheSnapshot.Sampler(7,0x8B5E,1,2)}) {
            Boundary boundary=new Boundary();boundary.overrideSampler=true;boundary.replacementSampler=sampler;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&boundary.save().equals(boundary.original),
                    "Inactive, array, non-sampler and unassigned/reserved units cannot succeed");
        }
    }
    private static void wrongBindingsAndStorageAreUnavailable() {
        for(SolarCacheSnapshot.Texture texture:new SolarCacheSnapshot.Texture[]{
                new SolarCacheSnapshot.Texture(999,true,34842,1024,512,0),new SolarCacheSnapshot.Texture(207,false,34842,1024,512,0),
                new SolarCacheSnapshot.Texture(207,true,34836,1024,512,0),new SolarCacheSnapshot.Texture(207,true,34842,1600,900,0),
                new SolarCacheSnapshot.Texture(207,true,34842,1024,512,1)}) {
            Boundary boundary=new Boundary();boundary.replacementTexture=texture;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored")),
                    "Declared allocation is not proof of actual named binding/storage");
        }
        for(SolarCacheSnapshot.Target target:new SolarCacheSnapshot.Target[]{null,
                new SolarCacheSnapshot.Target(107,207,"RGBA32F",1024,512),new SolarCacheSnapshot.Target(0,207,"RGBA16F",1024,512),
                new SolarCacheSnapshot.Target(107,107,"RGBA16F",1024,512),new SolarCacheSnapshot.Target(107,207,"RGBA16F",1024,511)}) {
            Boundary boundary=new Boundary();boundary.overrideTarget=true;boundary.replacementTarget=target;
            require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary).get("available")),
                    "A missing or incompatible real pipeline target cannot succeed");
        }
        Boundary boundary=new Boundary();boundary.aliasInputs=true;
        require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary).get("available")),
                "Cloudy C6 cannot masquerade as independent clear C7");
    }
    private static void invalidOrFailedReadbackRestoresStateAndRedactsMessages() {
        for(int invalid=0;invalid<8;invalid++) {
            Boundary boundary=new Boundary();float[] pixels=boundary.pixels.clone();
            if(invalid==0)pixels=null;else if(invalid==1)pixels=new float[7];else if(invalid==2)pixels[0]=Float.NaN;
            else if(invalid==3)pixels[1]=Float.POSITIVE_INFINITY;else if(invalid==4)pixels[0]=0;
            else if(invalid==5)pixels[0]=1.01f;else if(invalid==6)pixels[4]=0.125f;else pixels[7]=0;
            boundary.pixels=pixels;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))
                    &&boundary.save().equals(boundary.original),"Invalid cache readback cannot become positive evidence and must restore caller state");
        }
        Boundary boundary=new Boundary();boundary.readFailure=new InvocationTargetException(new IllegalArgumentException("secret-token /private/path"));
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))
                &&"IllegalArgumentException".equals(result.get("errorClass"))&&!result.toString().contains("secret-token")
                &&!result.toString().contains("/private/path"),"Failed reflected readback exports class only and restores state");
        boundary=new Boundary();boundary.changeProgramDuringRead=true;
        require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary).get("available")),
                "Changed current program cannot become same-frame evidence");
        boundary=new Boundary();boundary.changeFrameDuringRead=true;
        require(Boolean.FALSE.equals(SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary).get("available")),
                "Changed frame cannot become same-frame evidence");
    }
    private static void incompleteOrThrowingRestoreCannotClaimSuccess() {
        for(int omitted=0;omitted<11;omitted++) {
            Boundary boundary=new Boundary();boundary.omittedRestoreField=omitted;
            Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("stateRestored"))
                    &&result.get("stateBefore") instanceof Map<?,?>&&result.get("stateAfter") instanceof Map<?,?>,
                    "Every incompletely restored caller field invalidates the observation");
        }
        Boundary boundary=new Boundary();boundary.throwOnRestore=true;
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("stateRestored"))
                &&"IllegalStateException".equals(result.get("restoreErrorClass"))&&!result.toString().contains("secret-token"),
                "A throwing restoration is failure even if its state query appears restored");
    }
    private static void changedNamedAssignmentCannotBecomeConnectionEvidence() {
        Boundary boundary=new Boundary();boundary.changeSamplerDuringRead=true;
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
        require(Boolean.FALSE.equals(result.get("available")),"Changed live sampler assignment cannot become connection evidence");
        require(Boolean.TRUE.equals(result.get("stateRestored")),"Changed source assignment still restores observer caller state");
    }
    private static void observesNamedCurrentCacheAndRestoresCaller() {
        Boundary boundary=new Boundary();
        Map<String,Object> result=SolarCacheSnapshot.capture(201,"TRANSLUCENT",boundary);
        require(Boolean.TRUE.equals(result.get("available")),"Actual named current C7 must be available");
        require(Boolean.TRUE.equals(result.get("stateRestored"))&&boundary.save().equals(boundary.original),
                "All actual caller state must be restored");
        Map<?,?> source=(Map<?,?>)result.get("C7");
        require(Integer.valueOf(5).equals(source.get("unit"))&&Integer.valueOf(207).equals(source.get("textureId"))
                &&"alt".equals(source.get("pipelineSide")),"Follow live sampler unit and bound target7 alt, not index-as-unit");
        List<?> pixels=(List<?>)source.get("cacheTexels");
        require(List.of(0.875,0.75,0.5,1.0).equals(((Map<?,?>)pixels.get(0)).get("rgba")),
                "Export exact positive clear-cache values");
        require(List.of(0.0,0.0,0.0,1.0).equals(((Map<?,?>)pixels.get(1)).get("rgba")),
                "Export the actual black reserved-row neighbour");
        require(Boolean.TRUE.equals(result.get("scopeAuthorized"))&&Boolean.TRUE.equals(result.get("timingAcceptanceExcluded")),
                "Connection evidence is scoped and not frame-timing acceptance");
    }
    private static final class Boundary implements SolarCacheSnapshot.SystemBoundary {
        static final String[] MATRIX_NAMES={"gbufferProjection","gbufferProjectionInverse","gbufferModelView","gbufferModelViewInverse"};
        final SolarCacheSnapshot.State original=new SolarCacheSnapshot.State(33987,77,91,8,9,10,11,12,13,1,1);
        SolarCacheSnapshot.State state=original;
        boolean changeSamplerDuringRead,samplerChanged;
        boolean failProjectionStateQuery,projectionStateUnreadable;
        boolean projectionQueriesAllowed=true,replaceViewport;
        int projectionMutation=-1;
        String replaceUniform;
        ShoreSamplerSnapshot.Uniform replacementUniform;
        int[] replacementViewport;
        boolean allowGl=true,pipelineCurrent=true,overrideSampler,overrideTarget,aliasInputs,throwOnRestore;
        boolean changeProgramDuringRead,changeFrameDuringRead;
        int program=201,snapshotFrame=400,omittedRestoreField=-1;
        String phase="idle";
        SolarCacheSnapshot.Sampler replacementSampler;
        SolarCacheSnapshot.Target replacementTarget;
        SolarCacheSnapshot.Texture replacementTexture;
        Exception readFailure;
        float[] pixels={0.875f,0.75f,0.5f,1,0,0,0,1};
        BathymetrySnapshot.Scope scope=new BathymetrySnapshot.Scope(true,true,false,1,true,
                "AqualumenNaturalV2","b22dbccb-2970-41e6-847f-f183b1ec923d",308060,"minecraft:overworld",true,true);
        public SolarCacheSnapshot.Context context() {
            return new SolarCacheSnapshot.Context(scope,phase,pipelineCurrent);
        }
        public ShoreSamplerSnapshot.Uniform uniform(int program,String name) {
            glAllowed();require(projectionQueriesAllowed,"No matrix query without requested successful C7");
            if(name.equals(replaceUniform))return replacementUniform;
            for(int matrix=0;matrix<MATRIX_NAMES.length;matrix++)if(MATRIX_NAMES[matrix].equals(name)) {
                float[] values={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
                values[matrix*4]=matrix+0.125f;
                return new ShoreSamplerSnapshot.Uniform(20+matrix,0x8B5C,1,-1,values);
            }
            return new ShoreSamplerSnapshot.Uniform(30+(name.equals("isEyeInWater")?0:name.equals("viewWidth")?1:2),
                    name.equals("isEyeInWater")?0x1404:0x1406,1,-1,new float[]{name.equals("isEyeInWater")?1:name.equals("viewWidth")?1600:900});
        }
        public int[] viewport(){
            glAllowed();projectionStateUnreadable=failProjectionStateQuery;
            if(projectionMutation==0)program=202;
            if(projectionMutation==1)snapshotFrame++;
            if(projectionMutation==2)state=new SolarCacheSnapshot.State(state.active(),state.binding(),state.packBuffer(),state.alignment(),
                    state.rowLength(),state.imageHeight(),state.skipPixels(),state.skipRows()+1,state.skipImages(),state.swap(),state.lsb());
            return replaceViewport?replacementViewport:new int[]{0,0,1600,900};
        }
        private void glAllowed(){require(allowGl,"Unauthorized or measuring scope must never reach any GL boundary");}
        public int currentProgram(){glAllowed();return program;}
        public int frame(){return snapshotFrame;}
        public int maximumTextureUnits(){glAllowed();return 32;}
        public SolarCacheSnapshot.Sampler sampler(int program,String name) {
            glAllowed();if(name.equals("colortex7")&&overrideSampler)return replacementSampler;
            return new SolarCacheSnapshot.Sampler(name.equals("colortex7")?7:6,0x8B5E,1,name.equals("colortex7")?(samplerChanged?8:5):(aliasInputs?5:4));
        }
        public SolarCacheSnapshot.Target target(int index) {
            if(index==7&&overrideTarget)return replacementTarget;
            if(index==6&&aliasInputs)return new SolarCacheSnapshot.Target(207,306,"RGBA16F",1024,512);
            return new SolarCacheSnapshot.Target(100+index,200+index,"RGBA16F",1024,512);
        }
        public SolarCacheSnapshot.State save(){glAllowed();if(projectionStateUnreadable)throw new IllegalStateException("secret-token /private/path");return state;}
        public void selectUnit(int unit) {
            glAllowed();
            state=new SolarCacheSnapshot.State(33984+unit,unit==5?207:106,state.packBuffer(),state.alignment(),
                    state.rowLength(),state.imageHeight(),state.skipPixels(),state.skipRows(),state.skipImages(),state.swap(),state.lsb());
        }
        public SolarCacheSnapshot.Texture texture() {
            glAllowed();if(replacementTexture!=null)return replacementTexture;
            return new SolarCacheSnapshot.Texture(state.binding(),true,34842,1024,512,0);
        }
        public float[] readCacheTexels(SolarCacheSnapshot.Texture texture)throws Exception {
            glAllowed();
            state=new SolarCacheSnapshot.State(state.active(),state.binding(),0,4,0,0,0,0,0,0,0);
            samplerChanged=changeSamplerDuringRead;
            if(changeProgramDuringRead)program=202;if(changeFrameDuringRead)snapshotFrame++;
            if(readFailure!=null)throw readFailure;return pixels;
        }
        public void restore(SolarCacheSnapshot.State saved){
            glAllowed();
            projectionStateUnreadable=false;
            int[] before=values(state),after=values(saved);
            if(omittedRestoreField>=0)after[omittedRestoreField]=before[omittedRestoreField];
            state=new SolarCacheSnapshot.State(after[0],after[1],after[2],after[3],after[4],after[5],after[6],after[7],after[8],after[9],after[10]);
            if(throwOnRestore)throw new IllegalStateException("secret-token");
        }
        private static int[] values(SolarCacheSnapshot.State state) {
            return new int[]{state.active(),state.binding(),state.packBuffer(),state.alignment(),state.rowLength(),state.imageHeight(),
                    state.skipPixels(),state.skipRows(),state.skipImages(),state.swap(),state.lsb()};
        }
    }
    private static void require(boolean condition,String message) {
        if(!condition)throw new AssertionError(message);
    }
}
