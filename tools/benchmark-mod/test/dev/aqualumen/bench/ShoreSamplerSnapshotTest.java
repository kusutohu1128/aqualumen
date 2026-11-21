package dev.aqualumen.bench;

import java.lang.reflect.InvocationTargetException;
import java.util.List;
import java.util.Map;

/** Tests the public observer against only an external GL/Iris fixture. */
public final class ShoreSamplerSnapshotTest {
    public static void main(String[] args) {
        capturesActualNamedSourcesAndDeclinesMissingGeometry();
        rejectedStorageReportsActualBindingWithoutReadingPixels();
        failedRestorationIsObservableForEveryCallerField();
        System.out.println("PASS shore sampler snapshot CPU source/state contract; no runtime integration");
    }
    private static void capturesActualNamedSourcesAndDeclinesMissingGeometry() {
        Boundary boundary=new Boundary();
        Map<String,Object> result=ShoreSamplerSnapshot.capture(201,17,11,
                List.of(new ShoreSamplerSnapshot.Texel(3,4),new ShoreSamplerSnapshot.Texel(8,1)),boundary);
        require(Boolean.TRUE.equals(result.get("available")),"Named diagnostic sources must be captured");
        require(Boolean.TRUE.equals(result.get("stateRestored"))&&boundary.state.equals(boundary.original),
                "All eleven caller fields must be restored");
        require(Integer.valueOf(201).equals(result.get("program")),"Actual current program is recorded");
        List<?> sources=(List<?>)result.get("samplers");
        Map<?,?> refraction=(Map<?,?>)sources.get(0);
        require("colortex9".equals(refraction.get("name"))&&Integer.valueOf(5).equals(refraction.get("unit"))
                &&Integer.valueOf(70).equals(refraction.get("textureId")),"Source must follow live named unit and binding, not attachment number");
        List<?> samples=(List<?>)refraction.get("samples");
        require(List.of(0.125,18.0,-0.25,1.0).equals(((Map<?,?>)samples.get(0)).get("rgba")),
                "Exact finite HDR and negative float values must not be clamped or tone mapped");
        require(List.of(0.375,18.0,-0.0625,1.0).equals(((Map<?,?>)samples.get(1)).get("rgba")),
                "Selected integer texels must retain their coordinates and request order");
        require(Boolean.FALSE.equals(((Map<?,?>)sources.get(1)).get("active")),"Optimized-away sampler is explicitly inactive");
        List<?> maskSamples=(List<?>)((Map<?,?>)sources.get(2)).get("samples");
        require(List.of(0.125,36.0,-0.25,1.0).equals(((Map<?,?>)maskSamples.get(0)).get("rgba")),
                "A different live named texture must retain its own pixel values");
        require(Boolean.FALSE.equals(result.get("geometryUniformsAvailable"))
                &&Boolean.FALSE.equals(result.get("geometryAttributionAccepted")),"Missing matrix/camera inputs cannot become invented world coordinates");
        require(boundary.reads==2,"Read only the two actual active source textures");
        for(int program:new int[]{0,202}) {
            boundary=new Boundary();boundary.current=program;
            result=ShoreSamplerSnapshot.capture(201,17,11,List.of(new ShoreSamplerSnapshot.Texel(3,4)),boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))
                    &&"unknown_or_non_current_program".equals(result.get("reason"))&&boundary.reads==0,
                    "Absent or different current program must not supply a diagnostic source");
        }
        for(int kind=1;kind<=5;kind++) {
            boundary=new Boundary();boundary.samplerKind=kind;
            result=ShoreSamplerSnapshot.capture(201,17,11,List.of(new ShoreSamplerSnapshot.Texel(3,4)),boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))
                    &&boundary.reads==0,"Missing required sampler, wrong type/array size and invalid units must be rejected before reads");
        }
        boundary=new Boundary();boundary.geometryPresent=true;
        result=ShoreSamplerSnapshot.capture(201,17,11,List.of(new ShoreSamplerSnapshot.Texel(3,4)),boundary);
        require(Boolean.TRUE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("geometryUniformsAvailable"))
                &&Boolean.FALSE.equals(result.get("geometryAttributionAccepted")),
                "Even complete active geometry uniforms are observation, not accepted world reconstruction");
    }
    private static void rejectedStorageReportsActualBindingWithoutReadingPixels() {
        for(int kind=1;kind<=3;kind++) {
            Boundary boundary=new Boundary();boundary.storageKind=kind;
            Map<String,Object> result=ShoreSamplerSnapshot.capture(201,17,11,
                    List.of(new ShoreSamplerSnapshot.Texel(3,4)),boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))
                    &&"actual_binding_or_storage_mismatch".equals(result.get("reason")),
                    "16F, wrong-size and absent live textures must fail while restoring caller state");
            require(boundary.reads==0,"Rejected live storage must never be read as RGBA32F");
            Map<?,?> source=(Map<?,?>)((List<?>)result.get("samplers")).get(0);
            require(Integer.valueOf(kind==1?34842:34836).equals(source.get("actualFormat")),
                    "Storage rejection must still report observed format rather than a pack declaration");
            require(Integer.valueOf(kind==3?0:70).equals(source.get("textureId"))
                    &&Integer.valueOf(kind==2?16:17).equals(source.get("width")),
                    "Rejected binding and dimensions must remain inspectable");
        }
    }
    private static void failedRestorationIsObservableForEveryCallerField() {
        String[] fields={"active","binding","packBuffer","alignment","rowLength","imageHeight",
                "skipPixels","skipRows","skipImages","swap","lsb"};
        for(int field=0;field<fields.length;field++) {
            Boundary boundary=new Boundary();boundary.omittedRestoreField=field;
            Map<String,Object> result=ShoreSamplerSnapshot.capture(201,17,11,
                    List.of(new ShoreSamplerSnapshot.Texel(3,4)),boundary);
            require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("stateRestored"))
                    &&"state_restoration_failed".equals(result.get("reason")),"Every omitted caller field must invalidate observation");
            require(result.get("stateBefore") instanceof Map<?,?>&&result.get("stateAfter") instanceof Map<?,?>,
                    "Failed restoration must expose actual before/after state, not just a claimed boolean");
            Map<?,?> before=(Map<?,?>)result.get("stateBefore"),after=(Map<?,?>)result.get("stateAfter");
            require(before.size()==11&&after.size()==11,"Record all eleven observed state fields");
            for(int f=0;f<fields.length;f++)require(before.get(fields[f]).equals(after.get(fields[f]))==(f!=field),
                    "State evidence must identify precisely the non-restored field");
        }
        Boundary readFailure=new Boundary();readFailure.readFailure=true;
        Map<String,Object> result=ShoreSamplerSnapshot.capture(201,17,11,
                List.of(new ShoreSamplerSnapshot.Texel(3,4)),readFailure);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.TRUE.equals(result.get("stateRestored"))
                &&result.get("stateBefore").equals(result.get("stateAfter")),"Read failure must still restore and verify all state");
        require("IllegalArgumentException".equals(result.get("errorClass"))&&!result.toString().contains("private-token"),
                "Export failure class without private error messages");
        Boundary restoreFailure=new Boundary();restoreFailure.restoreFailure=true;
        result=ShoreSamplerSnapshot.capture(201,17,11,List.of(new ShoreSamplerSnapshot.Texel(3,4)),restoreFailure);
        require(Boolean.FALSE.equals(result.get("available"))&&Boolean.FALSE.equals(result.get("stateRestored"))
                &&result.get("stateAfter") instanceof Map<?,?>,"A throwing restore must still attempt the independent final state query");
    }
    private static final class Boundary implements ShoreSamplerSnapshot.SystemBoundary {
        final ShoreSamplerSnapshot.State original=new ShoreSamplerSnapshot.State(33987,77,9,8,12,16,2,3,4,1,1);
        ShoreSamplerSnapshot.State state=original;
        int current=201,reads,storageKind,samplerKind;
        int omittedRestoreField=-1;
        boolean readFailure,restoreFailure,geometryPresent;
        public int currentProgram() {return current;}
        public ShoreSamplerSnapshot.Viewport viewport() {return new ShoreSamplerSnapshot.Viewport(0,0,17,11);}
        public String renderer() {return "external CPU GL fixture, not a GPU";}
        public int maximumTextureUnits() {return 32;}
        public ShoreSamplerSnapshot.Uniform uniform(int program,String name) {
            if(name.equals("colortex9")) {
                if(samplerKind==1)return null;
                return new ShoreSamplerSnapshot.Uniform(2,samplerKind==2?0x8B62:0x8B5E,
                        samplerKind==3?2:1,samplerKind==4?32:samplerKind==5?-1:5,null);
            }
            if(name.equals("colortex11"))return new ShoreSamplerSnapshot.Uniform(4,0x8B5E,1,7,null);
            if(geometryPresent&&name.equals("cameraPosition"))
                return new ShoreSamplerSnapshot.Uniform(5,0x8B51,1,-1,new float[]{1,2,3});
            if(geometryPresent&&(name.equals("gbufferModelViewInverse")||name.equals("gbufferProjectionInverse"))) {
                float[] matrix=new float[16];for(int i=0;i<4;i++)matrix[i*5]=1;
                return new ShoreSamplerSnapshot.Uniform(6,0x8B5C,1,-1,matrix);
            }
            return null;
        }
        public ShoreSamplerSnapshot.State save() {return state;}
        public void selectUnit(int unit) {state=new ShoreSamplerSnapshot.State(33984+unit,unit==5?70:90,
                state.packBuffer(),state.alignment(),state.rowLength(),state.imageHeight(),state.skipPixels(),
                state.skipRows(),state.skipImages(),state.swap(),state.lsb());}
        public ShoreSamplerSnapshot.Texture texture() {
            return new ShoreSamplerSnapshot.Texture(storageKind==3?0:state.binding(),storageKind!=3,
                    storageKind==1?34842:34836,storageKind==2?16:17,11);
        }
        public float[] readTexels(ShoreSamplerSnapshot.Texture texture,List<ShoreSamplerSnapshot.Texel> texels) throws Exception {
            reads++;
            state=new ShoreSamplerSnapshot.State(state.active(),state.binding(),0,4,0,0,0,0,0,0,0);
            if(readFailure)throw new InvocationTargetException(new IllegalArgumentException("private-token"));
            float[] result=new float[texels.size()*4];
            for(int i=0;i<texels.size();i++) {
                ShoreSamplerSnapshot.Texel point=texels.get(i);
                result[4*i]=point.x()==3?0.125f:0.375f;
                result[4*i+1]=texture.id()==70?18.0f:36.0f;
                result[4*i+2]=-0.0625f*point.y();result[4*i+3]=1.0f;
            }
            return result;
        }
        public void restore(ShoreSamplerSnapshot.State saved) throws Exception {
            if(restoreFailure)throw new InvocationTargetException(new IllegalArgumentException("private-token"));
            int[] before={saved.active(),saved.binding(),saved.packBuffer(),saved.alignment(),saved.rowLength(),
                    saved.imageHeight(),saved.skipPixels(),saved.skipRows(),saved.skipImages(),saved.swap(),saved.lsb()};
            int[] now={state.active(),state.binding(),state.packBuffer(),state.alignment(),state.rowLength(),
                    state.imageHeight(),state.skipPixels(),state.skipRows(),state.skipImages(),state.swap(),state.lsb()};
            if(omittedRestoreField>=0)before[omittedRestoreField]=now[omittedRestoreField];
            state=new ShoreSamplerSnapshot.State(before[0],before[1],before[2],before[3],before[4],before[5],
                    before[6],before[7],before[8],before[9],before[10]);
        }
    }
    private static void require(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
}
