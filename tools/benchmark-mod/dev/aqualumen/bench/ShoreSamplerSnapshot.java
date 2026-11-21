package dev.aqualumen.bench;

import java.lang.reflect.InvocationTargetException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Standalone, unconnected observer for an authorized diagnostic FINAL pass.
 * The caller owns the world/pack/render-thread guard and one-shot invocation.
 * No shader execution, GL objects, uploads or error-flag queries occur here.
 */
public final class ShoreSamplerSnapshot {
    private static final int SAMPLER_2D=0x8B5E, FLOAT_MAT4=0x8B5C, FLOAT_VEC3=0x8B51;
    private static final int RGBA_32F=0x8814, MAX_TEXELS=16;
    private ShoreSamplerSnapshot() {}
    public record Texel(int x, int y) {}
    public record Viewport(int x, int y, int width, int height) {}
    public record Uniform(int location, int type, int size, int unit, float[] values) {}
    public record Texture(int id, boolean exists, int format, int width, int height) {}
    /** Actual caller state, including the binding on the original active unit. */
    public record State(int active, int binding, int packBuffer, int alignment, int rowLength,
            int imageHeight, int skipPixels, int skipRows, int skipImages, int swap, int lsb) {}
    /** Only the external Iris/OpenGL boundary may be substituted by CPU tests.
     * uniform returns null for an inactive name; never fabricated zero values.
     * readTexels returns exact level-zero RGBA floats in requested point order.
     * An adapter may use a verified subimage API or bounded reusable full-image
     * scratch storage; it must not create an FBO or consume GL error flags.
     * save/restore cover all eleven State fields. Texture bindings on selected
     * units must not be modified by observation.
     */
    public interface SystemBoundary {
        int currentProgram() throws Exception;
        Viewport viewport() throws Exception;
        String renderer() throws Exception;
        int maximumTextureUnits() throws Exception;
        Uniform uniform(int program, String name) throws Exception;
        State save() throws Exception;
        void selectUnit(int unit) throws Exception;
        Texture texture() throws Exception;
        float[] readTexels(Texture texture, List<Texel> texels) throws Exception;
        void restore(State state) throws Exception;
    }
    public static Map<String,Object> capture(int expectedProgram, int width, int height,
            List<Texel> texels, SystemBoundary boundary) {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("available",false);
        result.put("stateRestored",false);
        result.put("geometryUniformsAvailable",false);
        result.put("geometryAttributionAccepted",false);
        result.put("runtimeIntegrationAccepted",false);
        result.put("timingAcceptanceExcluded",true);
        result.put("visualQualityAccepted",false);
        result.put("tag","DEBUG-shore-sampler");
        result.put("reason","invalid_capture_request");
        if(boundary==null||expectedProgram<=0||width<=0||height<=0||width>16384||height>16384
                ||texels==null||texels.isEmpty()||texels.size()>MAX_TEXELS)return result;
        for(Texel point:texels)if(point==null||point.x()<0||point.y()<0||point.x()>=width||point.y()>=height)return result;
        List<Texel> points=List.copyOf(texels);
        State saved=null;
        try {
            result.put("reason","caller_state_unavailable");
            saved=boundary.save();
            if(saved==null)throw new IllegalStateException("Missing caller state");
            result.put("stateBefore",stateValues(saved));
            result.put("reason","unknown_or_non_current_program");
            int program=boundary.currentProgram();
            result.put("program",program);result.put("expectedProgram",expectedProgram);
            if(program!=expectedProgram)throw new IllegalStateException("Current program does not match");
            result.put("reason","final_viewport_mismatch");
            Viewport viewport=boundary.viewport();
            if(viewport==null||viewport.x()!=0||viewport.y()!=0||viewport.width()!=width||viewport.height()!=height)
                throw new IllegalStateException("Not the full expected FINAL viewport");
            result.put("width",width);result.put("height",height);
            result.put("renderer",boundary.renderer());
            result.put("maximumSelectedTexels",MAX_TEXELS);
            result.put("texelCoordinateConvention","integer level-zero texture coordinates; bottom-left origin");
            int units=boundary.maximumTextureUnits();
            if(units<=0)throw new IllegalStateException("No actual texture units");
            List<Map<String,Object>> sources=new ArrayList<>();
            result.put("samplers",sources);
            for(int index=9;index<=15;index++) {
                String name="colortex"+index;
                Map<String,Object> source=new LinkedHashMap<>();
                source.put("name",name);source.put("active",false);sources.add(source);
                result.put("reason","required_diagnostic_sampler_inactive");
                Uniform input=boundary.uniform(program,name);
                if(input==null||input.location()<0) {
                    source.put("reason","inactive_uniform");
                    if(index==9)throw new IllegalStateException("Diagnostic refraction sampler absent");
                    continue;
                }
                source.put("active",true);source.put("location",input.location());
                source.put("type",input.type());source.put("size",input.size());
                result.put("reason","named_sampler_type_or_unit_mismatch");
                if(input.type()!=SAMPLER_2D||input.size()!=1||input.unit()<0||input.unit()>=units)
                    throw new IllegalStateException("Not an assigned typed sampler2D");
                source.put("unit",input.unit());
                boundary.selectUnit(input.unit());
                result.put("reason","actual_binding_or_storage_mismatch");
                Texture texture=boundary.texture();
                if(texture!=null) {
                    source.put("textureId",texture.id());source.put("textureExists",texture.exists());
                    source.put("actualFormat",texture.format());
                    source.put("width",texture.width());source.put("height",texture.height());
                }
                if(texture==null||!texture.exists()||texture.id()<=0||texture.format()!=RGBA_32F
                        ||texture.width()!=width||texture.height()!=height)
                    throw new IllegalStateException("Live texture storage does not match");
                result.put("reason","bounded_float_readback_unavailable");
                float[] rgba=boundary.readTexels(texture,points);
                if(rgba==null||rgba.length!=points.size()*4)throw new IllegalStateException("Incomplete bounded RGBA readback");
                for(float value:rgba)if(!Float.isFinite(value))throw new IllegalStateException("Nonfinite observed pixel");
                List<Map<String,Object>> samples=new ArrayList<>();
                for(int p=0;p<points.size();p++) {
                    Texel point=points.get(p);
                    samples.add(Map.of("x",point.x(),"y",point.y(),"rgba",numbers(rgba,p*4,4)));
                }
                source.put("samples",samples);
                source.put("rawRgba32f",rgba.clone());
            }
            Map<String,Object> geometry=new LinkedHashMap<>();
            boolean complete=true;
            for(String name:new String[]{"gbufferModelViewInverse","gbufferProjectionInverse","cameraPosition"}) {
                int type=name.equals("cameraPosition")?FLOAT_VEC3:FLOAT_MAT4;
                int count=name.equals("cameraPosition")?3:16;
                Map<String,Object> observation=optionalGeometryUniform(boundary,program,name,type,count);
                geometry.put(name,observation);
                complete&=Boolean.TRUE.equals(observation.get("available"));
            }
            result.put("geometryUniforms",geometry);
            result.put("geometryUniformsAvailable",complete);
            result.put("geometryAttributionReason",complete?"uniforms_only_no_world_receiver_reconstruction":
                    "missing_or_invalid_active_geometry_uniforms");
            result.put("reason","program_changed_during_capture");
            if(boundary.currentProgram()!=program)throw new IllegalStateException("Program changed during observation");
            result.put("errorFlagPolicy","untouched; adapter must not consume or clear GL error flags");
            result.remove("reason");
            result.put("available",true);
        } catch(Exception|LinkageError error) {
            result.put("available",false);result.put("errorClass",errorClass(error));
        } finally {
            if(saved!=null) {
                Throwable restoreError=null;
                try {boundary.restore(saved);}
                catch(Exception|LinkageError error) {restoreError=error;}
                // A throwing restore cannot bypass the independent post-query.
                try {
                    State after=boundary.save();
                    if(after==null)throw new IllegalStateException("Restored state unavailable");
                    result.put("stateAfter",stateValues(after));
                    if(!saved.equals(after))throw new IllegalStateException("Incomplete caller state restoration");
                } catch(Exception|LinkageError error) {
                    if(restoreError==null)restoreError=error;
                    else result.put("stateQueryErrorClass",errorClass(error));
                }
                if(restoreError==null)result.put("stateRestored",true);
                else {
                    result.put("available",false);result.put("stateRestored",false);
                    result.put("reason","state_restoration_failed");result.put("restoreErrorClass",errorClass(restoreError));
                }
            }
        }
        return result;
    }
    private static Map<String,Object> optionalGeometryUniform(SystemBoundary boundary,int program,String name,int type,int count) {
        Map<String,Object> result=new LinkedHashMap<>();result.put("available",false);
        try {
            Uniform value=boundary.uniform(program,name);
            if(value==null||value.location()<0) {result.put("reason","inactive_uniform");return result;}
            result.put("location",value.location());result.put("type",value.type());result.put("size",value.size());
            if(value.type()!=type||value.size()!=1||value.values()==null||value.values().length!=count) {
                result.put("reason","incompatible_uniform");return result;
            }
            for(float component:value.values())if(!Float.isFinite(component)) {
                result.put("reason","nonfinite_uniform");return result;
            }
            result.put("values",numbers(value.values(),0,count));
            result.put("available",true);
        } catch(Exception|LinkageError error) {
            result.put("reason","uniform_query_failed");result.put("errorClass",errorClass(error));
        }
        return result;
    }
    private static List<Double> numbers(float[] values,int offset,int count) {
        List<Double> result=new ArrayList<>();
        for(int i=offset;i<offset+count;i++)result.add((double)values[i]);
        return result;
    }
    private static Map<String,Object> stateValues(State state) {
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("active",state.active());result.put("binding",state.binding());result.put("packBuffer",state.packBuffer());
        result.put("alignment",state.alignment());result.put("rowLength",state.rowLength());result.put("imageHeight",state.imageHeight());
        result.put("skipPixels",state.skipPixels());result.put("skipRows",state.skipRows());result.put("skipImages",state.skipImages());
        result.put("swap",state.swap());result.put("lsb",state.lsb());
        return result;
    }
    private static String errorClass(Throwable error) {
        while(error instanceof InvocationTargetException reflected&&reflected.getCause()!=null)error=reflected.getCause();
        return error.getClass().getSimpleName();
    }
}
