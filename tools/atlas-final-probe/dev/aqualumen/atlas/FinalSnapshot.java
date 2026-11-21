package dev.aqualumen.atlas;

import java.util.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Pure read boundary; real capture has no state setters or GL object creation. */
public final class FinalSnapshot {
    private FinalSnapshot() {}
    public record Scalar(int location,int type,int size,float value) {}
    public interface Boundary {
        int program() throws Exception;
        int frame() throws Exception;
        int[] viewport() throws Exception;
        Scalar scalar(int program,String name) throws Exception;
        Map<Integer,String> sources(int program) throws Exception;
        String renderer() throws Exception;
        String version() throws Exception;
    }
    public static Map<String,Object> capture(int expected,Boundary b) {
        Map<String,Object> out=new LinkedHashMap<>();out.put("available",false);
        out.put("readOnly",true);out.put("errorFlagConsumed",false);
        out.put("atlasTexelAddressesObserved",false);out.put("drawIssuedProven",false);
        out.put("physicalAccepted",false);out.put("visualAccepted",false);
        try {
            int frame=b.frame(),program=b.program();
            if(expected<=0||program!=expected||frame<0)throw new IllegalStateException("program");
            out.put("programBefore",program);out.put("frameBefore",frame);
            int[] viewport=b.viewport();
            if(viewport==null||viewport.length!=4||viewport[0]!=0||viewport[1]!=0||viewport[2]!=1600||viewport[3]!=900)
                throw new IllegalStateException("viewport");
            out.put("viewport",Arrays.stream(viewport).boxed().toList());
            Map<String,Object> uniforms=new LinkedHashMap<>();
            for(String name:List.of("viewWidth","viewHeight")) {
                Scalar s=b.scalar(program,name);float wanted=name.equals("viewWidth")?1600:900;
                if(s==null||s.location()<0||s.type()!=5126||s.size()!=1||!Float.isFinite(s.value())||s.value()!=wanted)
                    throw new IllegalStateException("view scalar");
                uniforms.put(name,Map.of("location",s.location(),"type",s.type(),"size",s.size(),"value",s.value()));
            }
            out.put("viewUniforms",uniforms);
            String renderer=b.renderer(),version=b.version();
            if(renderer==null||!renderer.contains("NVIDIA")||version==null)throw new IllegalStateException("renderer");
            out.put("renderer",renderer);out.put("GL",version);
            Map<Integer,String> sources=b.sources(program);
            if(sources==null||!sources.keySet().equals(Set.of(35633,35632)))throw new IllegalStateException("stages");
            List<Map<String,Object>> stages=new ArrayList<>();
            for(int type:List.of(35633,35632)) {
                String source=sources.get(type);byte[] bytes=source.getBytes(StandardCharsets.UTF_8);
                if(bytes.length==0||bytes.length>262144)throw new IllegalStateException("source size");
                stages.add(Map.of("type",type,"sourceBytes",bytes.length,"source",source,
                    "sourceSha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes))));
            }
            out.put("stages",stages);
            int after=b.program(),last=b.frame();
            boolean stable=program==after&&frame==last&&Arrays.equals(viewport,b.viewport());
            out.put("programAfter",after);out.put("frameAfter",last);out.put("programFrameViewportUnchanged",stable);
            out.put("available",stable);
        } catch(Exception|LinkageError e) {out.put("available",false);out.put("errorClass",e.getClass().getSimpleName());}
        return out;
    }
}
