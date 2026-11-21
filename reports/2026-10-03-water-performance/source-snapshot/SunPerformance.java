package dev.aqualumen.bench;

import java.nio.file.Path;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.StandardOpenOption;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.Field;
import java.util.Properties;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.IntSupplier;

/** TEST-only bounded observation. No permission decisions or cached live inputs. */
public final class SunPerformance {
    private SunPerformance() {}
    public interface Boundary { long nanoTime(); int irisFrame(); String phase(); }
    public interface CheckedBooleanSupplier { boolean getAsBoolean() throws Exception; }
    private static final int MAX_ROWS=4096,MAX_SUPPLIERS=256;
    private static Boundary boundary;
    private static boolean profiling,available,finished;
    private static String mode="inactive",run="";
    private static Path directory;
    private static int registrations;
    private static long calls,authorized,rejected,originalThrows,failures;
    private static long hashCalls,hashBytes,hashNs,unownedHashCalls,unownedHashBytes,unownedHashNs,nestedSuppliers;
    private static final Map<Key,Row> rows=new LinkedHashMap<>();
    private static final ThreadLocal<Span> current=new ThreadLocal<>();
    private static final ThreadLocal<HashSpan> hashing=new ThreadLocal<>();
    private record Key(int frame,int supplier,String phase) {}
    private static final class Row {
        final Key key;long calls,authorized,rejected,throwsCount,totalNs,hashCalls,hashBytes,hashNs;
        Row(Key key){this.key=key;}
    }
    private record Span(Row row,long start,Span parent) {}
    private record HashSpan(Span owner,long start,HashSpan parent) {}
    public static void begin(String requested,String id,Path output,Boundary external) {
        mode=requested;run=id;directory=output.toAbsolutePath().normalize();boundary=external;finished=false;
        profiling="profile".equals(requested);available=profiling||"control".equals(requested);
        calls=authorized=rejected=originalThrows=failures=0;
        hashCalls=hashBytes=hashNs=unownedHashCalls=unownedHashBytes=unownedHashNs=nestedSuppliers=0;
        rows.clear();current.remove();hashing.remove();
    }
    public static IntSupplier wrap(IntSupplier original) {
        final int id=++registrations;
        return ()->{
            if(!profiling)return original.getAsInt();
            Span parent=current.get(),span=null;boolean returned=false;int value=0;
            try {
                try {
                    calls++;
                    if(parent!=null){nestedSuppliers++;available=false;}
                    int frame=boundary.irisFrame();String phase=boundary.phase();
                    if(frame<0||phase==null||id>MAX_SUPPLIERS)throw new IllegalStateException("unavailable metadata or bounds");
                    Key key=new Key(frame,id,phase);Row row=rows.get(key);
                    if(row==null){if(rows.size()>=MAX_ROWS)throw new IllegalStateException("row bound");row=new Row(key);rows.put(key,row);}
                    row.calls++;span=new Span(row,boundary.nanoTime(),parent);current.set(span);
                } catch(Throwable observationFailure){fault();current.remove();}
                value=original.getAsInt();returned=true;return value;
            } finally {
                try {
                    if(returned){if(value==1)authorized++;else if(value==0)rejected++;else fault();}
                    else originalThrows++;
                    if(span!=null){Row row=span.row();if(returned){if(value==1)row.authorized++;else if(value==0)row.rejected++;}
                        else row.throwsCount++;long delta=boundary.nanoTime()-span.start();if(delta<0)fault();else row.totalNs+=delta;}
                } catch(Throwable observationFailure){fault();}
                finally {try{if(parent==null)current.remove();else current.set(parent);}catch(Throwable observationFailure){fault();}}
            }
        };
    }
    /** Times the original complete read/digest/hex/equality expression exactly once. */
    public static boolean hash(CheckedBooleanSupplier original) throws Exception {
        if(!profiling)return original.getAsBoolean();
        HashSpan parent=hashing.get(),span=null;
        try {
            try {
                Span owner=current.get();
                if(owner==null)unownedHashCalls++;else{hashCalls++;owner.row().hashCalls++;}
                span=new HashSpan(owner,boundary.nanoTime(),parent);hashing.set(span);
            } catch(Throwable observationFailure){fault();hashing.remove();}
            return original.getAsBoolean();
        } finally {
            try {
                if(span!=null){long delta=boundary.nanoTime()-span.start();
                    if(delta<0)fault();else if(span.owner()==null)unownedHashNs+=delta;
                    else{hashNs+=delta;span.owner().row().hashNs+=delta;}}
            }catch(Throwable observationFailure){fault();}
            finally {try{if(parent==null)hashing.remove();else hashing.set(parent);}catch(Throwable observationFailure){fault();}}
        }
    }
    /** Identity observer of the one original readAllBytes result; never reads/copies. */
    public static byte[] bytes(byte[] original) {
        if(profiling)try{
            HashSpan span=hashing.get();if(span!=null){
                if(span.owner()==null)unownedHashBytes+=original.length;
                else{hashBytes+=original.length;span.owner().row().hashBytes+=original.length;}
            }
        }catch(Throwable observationFailure){fault();}
        return original;
    }
    /** Called only after the original benchmark setup guard succeeds. */
    public static void onRunReady(String id,Path output,Properties config) {
        try {
            if(id.equals(run)&&output.toAbsolutePath().normalize().equals(directory))return;
            String requested=config.getProperty("sun_profile","control");
            if(!"profile".equals(requested)&&!"control".equals(requested)){
                begin("invalid-mode",id,output,null);return;
            }
            Boundary external=null;
            if("profile".equals(requested))try{
                Field state=Recorder.class.getDeclaredField("state");state.setAccessible(true);
                Object value=Class.forName("net.irisshaders.iris.uniforms.SystemTimeUniforms").getField("COUNTER").get(null);
                if(!(value instanceof IntSupplier frame))throw new IllegalStateException("actual Iris counter unavailable");
                external=new Boundary(){
                    public long nanoTime(){return System.nanoTime();}
                    public int irisFrame(){return frame.getAsInt();}
                    public String phase(){try{return (String)state.get(null);}catch(Exception failure){throw new IllegalStateException(failure);}}
                };
            }catch(Throwable observationFailure){/* begin below keeps real checks and records unavailable metadata */}
            begin(requested,id,output,external);
            if(profiling&&external==null)fault();
        }catch(Throwable observationFailure){fault();}
    }
    /** Exact Recorder completion callback, before optional client quit; no sample I/O. */
    public static boolean finish(String phase,String id,Path output) {
        try {
            if(!"complete".equals(phase)||!id.equals(run)||finished||directory==null
                    ||!directory.equals(output.toAbsolutePath().normalize())
                    ||(!"profile".equals(mode)&&!"control".equals(mode)))return false;
            finished=true;
            if(!Files.isDirectory(directory,LinkOption.NOFOLLOW_LINKS)||!directory.equals(directory.toRealPath())){fault();return false;}
            Path destination=directory.resolve("sun-profile.json");
            if(Files.exists(destination,LinkOption.NOFOLLOW_LINKS)){fault();return false;}
            Files.writeString(destination,snapshot()+"\n",StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
            return true;
        }catch(Throwable observationFailure){fault();return false;}
    }
    private static void fault(){available=false;failures++;}
    private static String quote(String text){return "\""+text.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";}
    public static String snapshot() {
        StringBuilder out=new StringBuilder("{\"schema\":\"aqualumen-sun-profile-v1\",\"mode\":").append(quote(mode))
            .append(",\"runId\":").append(quote(run)).append(",\"timingsMeasured\":").append(profiling)
            .append(",\"metricsAvailable\":").append(available).append(",\"measurementFailures\":").append(failures)
            .append(",\"supplierCalls\":").append(profiling?Long.toString(calls):"null")
            .append(",\"authorized\":").append(profiling?Long.toString(authorized):"null")
            .append(",\"rejected\":").append(profiling?Long.toString(rejected):"null")
            .append(",\"originalThrows\":").append(profiling?Long.toString(originalThrows):"null")
            .append(",\"hashCalls\":").append(profiling?Long.toString(hashCalls):"null")
            .append(",\"hashBytes\":").append(profiling?Long.toString(hashBytes):"null")
            .append(",\"fullHashExpressionNs\":").append(profiling?Long.toString(hashNs):"null")
            .append(",\"unownedHashCalls\":").append(profiling?Long.toString(unownedHashCalls):"null")
            .append(",\"unownedHashBytes\":").append(profiling?Long.toString(unownedHashBytes):"null")
            .append(",\"unownedFullHashExpressionNs\":").append(profiling?Long.toString(unownedHashNs):"null")
            .append(",\"nestedSuppliers\":").append(profiling?Long.toString(nestedSuppliers):"null")
            .append(",\"hashMetric\":\"getInstance/readAllBytes/digest/hex/equals; nested within supplier total, not isolated SHA\" ")
            .append(",\"maximumRows\":").append(MAX_ROWS).append(",\"maximumRegistrationIds\":").append(MAX_SUPPLIERS)
            .append(",\"rows\":[");
        boolean comma=false;for(Row row:rows.values()){
            if(comma)out.append(',');comma=true;
            out.append("{\"frame\":").append(row.key.frame()).append(",\"supplierId\":").append(row.key.supplier())
                .append(",\"phase\":").append(quote(row.key.phase())).append(",\"calls\":").append(row.calls)
                .append(",\"authorized\":").append(row.authorized).append(",\"rejected\":").append(row.rejected)
                .append(",\"originalThrows\":").append(row.throwsCount).append(",\"totalAuthorizationNs\":").append(row.totalNs)
                .append(",\"hashCalls\":").append(row.hashCalls).append(",\"hashBytes\":").append(row.hashBytes)
                .append(",\"fullHashExpressionNs\":").append(row.hashNs).append('}');
        }
        return out.append("]}").toString();
    }
}
