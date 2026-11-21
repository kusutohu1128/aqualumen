package dev.aqualumen.stageprobe;

import dev.aqualumen.bench.BathymetrySnapshot;
import dev.aqualumen.bench.ShoreRuntimeObserver;
import java.lang.reflect.InvocationTargetException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

/** TEST-only actual linked-stage observation; injectable external read boundary. */
public final class StageSnapshot {
    private StageSnapshot() {}
    public record Context(Properties configuration, BathymetrySnapshot.Scope scope,
            boolean measurementIdle, int expectedProgram, boolean includeSources) {}
    public record Capabilities(String version, String renderer, boolean arbTessellation, boolean openGL40) {}
    public interface Boundary {
        boolean usingTessellation() throws Exception;
        int frame() throws Exception;
        int currentProgram() throws Exception;
        int programParameter(int program, int parameter) throws Exception;
        int[] attachedShaders(int program, int maximum) throws Exception;
        int shaderType(int shader) throws Exception;
        String shaderSource(int shader, int maximumBytes) throws Exception;
        int patchVertices() throws Exception;
        Capabilities capabilities() throws Exception;
    }
    public static Map<String,Object> capture(Context context, Boundary boundary) {
        if(context==null||!ShoreRuntimeObserver.acceptsConfiguration(context.configuration())
                ||!ShoreRuntimeObserver.acceptsScope(context.scope()))
            return Map.of("available",false,"reason","outside_authorized_test_scope");
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("available",false);
        result.put("scope","terrain-tessellation-stages");
        result.put("naturalVisualAccepted",false);
        result.put("exclusiveWaterProgramProven",false);
        result.put("readOnly",true);
        result.put("errorFlagConsumed",false);
        if(!context.measurementIdle()) {
            result.put("reason","benchmark_not_idle");return result;
        }
        int frameBefore=-1,programBefore=-1;
        boolean glStarted=false,qualified=false;
        try {
            if(boundary==null||!boundary.usingTessellation()) {
                result.put("reason","not_using_tessellation");return result;
            }
            if(context.expectedProgram()<=0)throw new IllegalStateException();
            frameBefore=boundary.frame();
            glStarted=true;
            programBefore=boundary.currentProgram();
            result.put("frameBefore",frameBefore);result.put("programBefore",programBefore);
            result.put("constructorProgram",context.expectedProgram());
            if(programBefore!=context.expectedProgram()||frameBefore<0)throw new IllegalStateException();
            Capabilities capabilities=boundary.capabilities();
            if(capabilities==null||!bounded(capabilities.version())||!bounded(capabilities.renderer())
                    ||!(capabilities.arbTessellation()||capabilities.openGL40()))throw new IllegalStateException();
            result.put("capabilities",Map.of("version",capabilities.version(),"renderer",capabilities.renderer(),
                    "GL_ARB_tessellation_shader",capabilities.arbTessellation(),"OpenGL40",capabilities.openGL40()));
            int linked=boundary.programParameter(programBefore,35714);
            result.put("linkStatus",linked);
            if(linked!=1)throw new IllegalStateException();
            int count=boundary.programParameter(programBefore,35717);
            if(count<1||count>8)throw new IllegalStateException();
            int[] attached=boundary.attachedShaders(programBefore,8);
            if(attached==null||attached.length!=count)throw new IllegalStateException();
            result.put("attachedShaderCount",count);
            List<Map<String,Object>> stages=new ArrayList<>();
            HashSet<Integer> ids=new HashSet<>(),types=new HashSet<>();
            for(int shader:attached) {
                if(shader<=0||!ids.add(shader))throw new IllegalStateException();
                int type=boundary.shaderType(shader);
                String label=stageName(type);
                if(label==null||!types.add(type))throw new IllegalStateException();
                Map<String,Object> stage=new LinkedHashMap<>();
                stage.put("shader",shader);stage.put("type",type);stage.put("stage",label);
                if(context.includeSources()) {
                    String source=boundary.shaderSource(shader,262144);
                    if(source==null||source.isEmpty())throw new IllegalStateException();
                    byte[] bytes=source.getBytes(StandardCharsets.UTF_8);
                    if(bytes.length>262144)throw new IllegalStateException();
                    stage.put("sourceBytes",bytes.length);
                    stage.put("sourceSha256",java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
                    if(type==36487)result.put("tesSourceMarkerPresent",source.contains("tessStageCoord")&&source.contains("gl_TessCoord"));
                }
                stages.add(stage);
            }
            result.put("stages",stages);
            if(!types.equals(java.util.Set.of(35633,36488,36487,35632)))throw new IllegalStateException();
            int outputVertices=boundary.programParameter(programBefore,36469);
            int patchVertices=boundary.patchVertices();
            result.put("tessControlOutputVertices",outputVertices);
            result.put("patchVertices",patchVertices);
            if(outputVertices!=3||patchVertices!=3)throw new IllegalStateException();
            qualified=true;
        } catch(Exception|LinkageError failure) {
            result.put("errorClass",errorClass(failure));
        } finally {
            if(glStarted) {
                try {
                    int programAfter=boundary.currentProgram(),frameAfter=boundary.frame();
                    boolean unchanged=programAfter==programBefore&&frameAfter==frameBefore;
                    result.put("programAfter",programAfter);result.put("frameAfter",frameAfter);
                    result.put("programAndFrameUnchanged",unchanged);
                    qualified&=unchanged;
                } catch(Exception|LinkageError failure) {
                    result.put("programAndFrameUnchanged",false);
                    result.put("errorClass",errorClass(failure));qualified=false;
                }
            }
        }
        result.put("available",qualified);return result;
    }
    private static boolean bounded(String value){return value!=null&&!value.isBlank()&&value.length()<=256;}
    private static String stageName(int type) {
        return switch(type){case 35633->"vertex";case 36488->"tess_control";case 36487->"tess_evaluation";case 35632->"fragment";default->null;};
    }
    private static String errorClass(Throwable failure) {
        while(failure instanceof InvocationTargetException invocation&&invocation.getCause()!=null)failure=invocation.getCause();
        return failure.getClass().getSimpleName();
    }
}
