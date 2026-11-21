package dev.aqualumen.suntest;

import java.util.Map;
import java.util.LinkedHashMap;
import java.util.Set;

/** Prepared current uniform only, not a draw/fragment/WNS or PNG observation. */
public final class SunGuardSnapshot {
    private SunGuardSnapshot() {}
    public record Context(SunAuthorization.SystemBoundary authorization,String phase,String pass,
            boolean containsTessellation,boolean currentPipelineMatches,int constructorProgram) {}
    public record Uniform(String name,int location,int type,int size) {}
    public interface SystemBoundary {
        int frame() throws Exception;
        int currentProgram() throws Exception;
        Uniform uniform(int program,String name) throws Exception;
        int integerUniform(int program,int location) throws Exception;
    }
    public static Map<String,Object> capture(Context context,SystemBoundary boundary) {
        Map<String,Object> result=new LinkedHashMap<>();result.put("available",false);
        result.put("scope","prepared-current-translucent-int-uniform");result.put("readOnly",true);
        result.put("errorFlagConsumed",false);result.put("drawIssuedProven",false);
        result.put("fragmentFetchProven",false);result.put("WNSApplicationProven",false);result.put("pngSameFrameProven",false);
        if(context==null||SunAuthorization.value(context.authorization())!=1
                ||!Set.of("idle","complete","aborted").contains(context.phase()==null?"":context.phase())
                ||!"TRANSLUCENT".equals(context.pass())||!context.containsTessellation()
                ||!context.currentPipelineMatches()||context.constructorProgram()<=0) {
            result.put("reason","outside_authorized_idle_translucent_scope");return result;
        }
        result.put("supplierAuthorization",1);result.put("constructorProgram",context.constructorProgram());
        int frameBefore=-1,programBefore=-1;boolean started=false,qualified=false;
        try {
            frameBefore=boundary.frame();programBefore=boundary.currentProgram();started=true;
            result.put("frameBefore",frameBefore);result.put("programBefore",programBefore);
            if(frameBefore<0||programBefore!=context.constructorProgram())throw new IllegalStateException();
            Uniform uniform=boundary.uniform(programBefore,"aqualumenSunTestAuthorized");
            if(uniform==null||!"aqualumenSunTestAuthorized".equals(uniform.name())||uniform.location()<0
                    ||uniform.type()!=5124||uniform.size()!=1)throw new IllegalStateException();
            int value=boundary.integerUniform(programBefore,uniform.location());
            result.put("uniform",Map.of("name",uniform.name(),"active",true,"location",uniform.location(),
                "type",uniform.type(),"size",uniform.size(),"value",value));
            if(value!=1)throw new IllegalStateException();qualified=true;
        } catch(Exception|LinkageError failure) {result.put("errorClass",errorClass(failure));}
        finally {
            if(started)try {
                int programAfter=boundary.currentProgram(),frameAfter=boundary.frame();
                result.put("programAfter",programAfter);result.put("frameAfter",frameAfter);
                boolean unchanged=programAfter==programBefore&&frameAfter==frameBefore;
                result.put("programAndFrameUnchanged",unchanged);qualified&=unchanged;
            } catch(Exception|LinkageError failure) {
                result.put("programAndFrameUnchanged",false);result.put("errorClass",errorClass(failure));qualified=false;
            }
        }
        result.put("available",qualified);return result;
    }
    private static String errorClass(Throwable error) {
        while(error instanceof java.lang.reflect.InvocationTargetException e&&e.getCause()!=null)error=e.getCause();
        return error.getClass().getSimpleName();
    }
}
