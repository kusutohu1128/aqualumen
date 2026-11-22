package dev.aqualumen.profiler;

import dev.aqualumen.animalqa.FrameSample;
import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.shadows.ShadowRenderingState;
import net.caffeinemc.mods.sodium.client.render.chunk.terrain.DefaultTerrainRenderPasses;
import org.lwjgl.opengl.GL;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.ArrayBlockingQueue;
import static org.lwjgl.opengl.GL11.*;
import static org.lwjgl.opengl.GL15.*;
import static org.lwjgl.opengl.GL33.*;

public final class Timers {
    static final int CAP=256, SLOTS=16, LAG=8;
    record ProgramName(String pass,String draw) {}
    static final Map<Object,ProgramName> names=new IdentityHashMap<>();
    record PassLabel(String name, boolean empty) {}
    static final Map<Object,PassLabel> passNames=new IdentityHashMap<>();
    static ProgramName selected;
    static String stage="unnamed", currentPass="unnamed";
    static int passIndex;
    static boolean inPass, initialized;
    static long epoch=1, frame;
    static Slot active;
    static final QueryPolicy nesting=new QueryPolicy();
    static final Slot[] ring=new Slot[SLOTS];
    static final ArrayBlockingQueue<String> pending=new ArrayBlockingQueue<>(64);
    static Path game;
    static Boolean opted;
    static volatile Throwable writeError;
    static boolean queryBuffers;
    static Object context;

    static class Slot {
        final int[] queries=new int[CAP], stack=new int[CAP], parent=new int[CAP],
                begin=new int[CAP], end=new int[CAP], draws=new int[CAP];
        final long[] times=new long[CAP];
        final String[] labels=new String[CAP];
        final BitSet[] emptySlots=new BitSet[CAP];
        int marks, ranges, depth;
        long id, epoch;
        boolean abandoned;
        Slot(){glGenQueries(queries);}
        int stamp(){int i=marks++; glQueryCounter(queries[i],GL_TIMESTAMP); return i;}
        void open(String name){
            if(abandoned) return;
            // Leave enough room for every open interval and the terminal availability query.
            if(!QueryPolicy.room(marks,depth,CAP)){abandoned=true; return;}
            int i=ranges++;
            labels[i]=name; draws[i]=0;
            if(emptySlots[i]!=null) emptySlots[i].clear();
            parent[i]=depth==0?-1:stack[depth-1];
            stack[depth++]=i;
            begin[i]=stamp();
        }
        void close(){
            if(abandoned) return;
            if(depth==0) throw new IllegalStateException("GPU range stack underflow");
            end[stack[--depth]]=stamp();
        }
        void empty(int index){
            if(abandoned) return;
            int parent=stack[depth-1];
            if(emptySlots[parent]==null) emptySlots[parent]=new BitSet();
            emptySlots[parent].set(index);
        }
        String rows(){
            for(int j=0;j<marks;j++) times[j]=glGetQueryObjectui64(queries[j],GL_QUERY_RESULT);
            StringBuilder text=new StringBuilder(8192);
            for(int i=0;i<ranges;i++){
                text.append(epoch).append(',').append(id).append(',').append(labels[i]).append(',')
                    .append(times[begin[i]]).append(',').append(times[end[i]]).append(',').append(parent[i])
                    .append(',').append(draws[i]).append(',');
                BitSet visited=emptySlots[i];
                if(visited!=null){
                    for(int first=visited.nextSetBit(0);first>=0;){
                        int next=visited.nextClearBit(first);
                        if(first!=visited.nextSetBit(0)) text.append('|');
                        text.append(first);
                        if(next>first+1) text.append('-').append(next-1);
                        first=visited.nextSetBit(next);
                    }
                }
                text.append('\n');
            }
            return text.toString();
        }
    }

    private static boolean opted(){
        if(opted!=null) return opted;
        try{
            game=FabricLoader.getInstance().getGameDir().toRealPath();
            opted=false;
            if(!game.toString().matches("/tmp/aql-v190-run-[^/]+/minecraft")) return false;
            Path marker=game.resolve("config/gpu-profile.properties");
            if(!Files.isRegularFile(marker,LinkOption.NOFOLLOW_LINKS)) return false;
            Properties p=new Properties(), iris=new Properties();
            try(var reader=Files.newBufferedReader(marker)){p.load(reader);}
            try(var reader=Files.newBufferedReader(game.resolve("config/iris.properties"))){iris.load(reader);}
            String pack=iris.getProperty("shaderPack");
            if(!game.toString().equals(p.getProperty("game")) || !p.getProperty("label","").matches("gp-[a-z0-9-]+")
                    || !p.getProperty("pack","").equals(pack) || !pack.matches("[A-Za-z0-9.\\-]+\\.zip"))
                throw new IllegalStateException("invalid private profiler marker");
            Path archive=game.resolve("shaderpacks").resolve(pack);
            String hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(archive)));
            if(!hash.equals(p.getProperty("sha256"))) throw new IllegalStateException("private pack hash");
            opted=true;
            return true;
        } catch(Exception e){throw new IllegalStateException("profiler guard",e);}
    }

    private static void init(){
        var caps=GL.getCapabilities();
        if(!(caps.OpenGL33 || caps.GL_ARB_timer_query) || glGetQueryi(GL_TIMESTAMP,GL_QUERY_COUNTER_BITS)<32)
            throw new IllegalStateException("timer query unavailable");
        context=caps;
        queryBuffers=caps.OpenGL44 || caps.GL_ARB_query_buffer_object;
        int[] bindings={0x8B8D,0x8CA6,0x8CAA,0x85B5,0x84E0}; // program, draw/read FBO, VAO, active texture
        int[] before=Arrays.stream(bindings).map(p->glGetInteger(p)).toArray();
        for(int i=0;i<SLOTS;i++) ring[i]=new Slot();
        glQueryCounter(ring[0].queries[0],GL_TIMESTAMP);
        if(!Arrays.equals(before,Arrays.stream(bindings).map(p->glGetInteger(p)).toArray()))
            throw new IllegalStateException("timer setup changed GL bindings");
        System.out.println("AQ_PROFILE_STATE bindings preserved");
        try{
            BufferedWriter out=Files.newBufferedWriter(game.resolve("gpu-frames.csv"),StandardOpenOption.CREATE_NEW);
            out.write("epoch,frame,range,start_ns,end_ns,parent,draws,empty_slots\n"); out.flush();
            Thread writer=new Thread(()->{
                try(out){for(;;){out.write(pending.take());out.flush();}}
                catch(Exception e){writeError=e;}
            },"Aqualumen private timestamp writer");
            writer.setDaemon(true); writer.start();
        }catch(IOException e){throw new UncheckedIOException(e);}
        initialized=true;
        System.out.println("AQ_PROFILE_READY bits="+glGetQueryi(GL_TIMESTAMP,GL_QUERY_COUNTER_BITS)+" renderer="+glGetString(GL_RENDERER));
    }

    public static void frameStart(Object client){
        if(!nesting.enter()){
            // The frame ordinal is assigned on return. No recursive transition frame is publishable.
            if(active!=null){active.abandoned=true; active=null; inPass=false;}
            return;
        }
        if(!opted() || !FrameSample.authorized(client)) return;
        if(!initialized) init();
        if(GL.getCapabilities()!=context || writeError!=null) throw new IllegalStateException("profiler context or writer",writeError);
        if(active!=null) throw new IllegalStateException("unfinished frame");
        frame=FrameSample.issuingOrdinal();
        // One steady readback per frame. A late slot remains owned until GPU completion.
        boolean canRead=!queryBuffers || glGetInteger(0x9193)==0; // GL_QUERY_BUFFER_BINDING
        for(Slot s:ring){
            if(!canRead || !QueryPolicy.harvest(frame,s.id,LAG)) continue;
            if(glGetQueryObjecti(s.queries[s.marks-1],GL_QUERY_RESULT_AVAILABLE)==0) continue;
            if(!s.abandoned && !pending.offer(s.rows())) System.out.println("AQ_PROFILE_DROP writer "+s.id);
            s.id=0;
        }
        Slot s=ring[(int)(frame%SLOTS)];
        if(s.id!=0){System.out.println("AQ_PROFILE_DROP ring "+frame);return;}
        s.id=frame;s.epoch=epoch;s.depth=s.ranges=s.marks=0;s.abandoned=false;
        active=s; inPass=false;
        open("frame");
    }
    public static void leaveFrame(){nesting.leave();}
    public static void shutdown(){
        if(initialized && GL.getCapabilities()==context){
            for(Slot s:ring) glDeleteQueries(s.queries);
            initialized=false;
        }
    }
    public static void frameEnd(){
        if(!nesting.outer() || active==null) return;
        if(!active.abandoned && active.depth!=1) throw new IllegalStateException("unbalanced profile "+active.depth);
        close();
        if(active.abandoned) System.out.println("AQ_PROFILE_DROP budget/reload "+frame);
        active=null; inPass=false;
    }
    public static void open(String s){
        if(active==null) return;
        if(s.startsWith("stage/")){
            stage=s; passIndex=0; currentPass=s;
        }
        active.open(s);
    }
    public static void close(){if(active!=null) active.close();}
    public static void countDraw(){if(active!=null && !active.abandoned) active.draws[active.stack[active.depth-1]]++;}

    public static void register(Object program,Object source){
        if(program==null || !opted()) return;
        if(program instanceof Object[] programs){
            Object[] sources=(Object[])source;
            if(sources.length!=programs.length) throw new IllegalStateException("compute source alignment");
            for(int i=0;i<programs.length;i++) register(programs[i],sources[i]);
        }else{
            try{
                String n=(String)source.getClass().getMethod("getName").invoke(source);
                boolean compute=source instanceof net.irisshaders.iris.shaderpack.programs.ComputeSource;
                names.put(program,new ProgramName("pass/"+n,(compute?"dispatch/":"quad/")+n));
            }catch(ReflectiveOperationException e){throw new IllegalStateException(e);}
        }
    }
    private static Object field(Object obj,String name) throws ReflectiveOperationException {
        for(Class<?> c=obj.getClass();c!=null;c=c.getSuperclass()){
            try{var f=c.getDeclaredField(name);f.setAccessible(true);return f.get(obj);}
            catch(NoSuchFieldException ignored){}
        }
        throw new NoSuchFieldException(name);
    }
    static PassLabel passLabel(Object pass,String stage,int ordinal){
        try{
            Object raster=field(pass,"program");
            ProgramName mapped=names.get(raster);
            boolean empty=raster==null;
            if(mapped!=null) return new PassLabel(mapped.pass(),false);
            Object[] computes=(Object[])field(pass,"computes");
            if(computes!=null){
                for(Object compute:computes){
                    if(compute==null) continue;
                    empty=false;
                    mapped=names.get(compute);
                    if(mapped!=null) return new PassLabel(mapped.pass(),false);
                }
            }
            return new PassLabel(stage+"/unnamed-"+ordinal,empty);
        }catch(ReflectiveOperationException e){throw new IllegalStateException(e);}
    }
    public static void pass(Object pass){
        if(active==null || active.abandoned) return;
        if(inPass) throw new IllegalStateException("nested pass loop");
        int index=passIndex++;
        PassLabel label=passNames.get(pass);
        if(label==null){
            label=passLabel(pass,stage,index);
            passNames.put(pass,label);
            if(!label.name().startsWith("pass/"))
                System.out.println("AQ_PROFILE_SLOT "+label.name()+" empty="+label.empty());
        }
        currentPass=label.name();
        if(label.empty()){
            // No draw or dispatch. Preserve the visit in its timed stage, without two queries per null slot.
            active.empty(index);
            return;
        }
        open(currentPass); inPass=true;
    }
    public static void endPass(){if(inPass){close();inPass=false;}}
    public static void select(Object p){if(active!=null) selected=names.get(p);}
    public static void draw(boolean compute){
        if(active==null) return;
        String label=selected==null?(compute?"dispatch/":"quad/")+currentPass:selected.draw();
        open(label);countDraw();
    }
    public static void terrain(Object pass){
        if(active==null) return;
        boolean shadow=ShadowRenderingState.areShadowsCurrentlyBeingRendered();
        if(pass==DefaultTerrainRenderPasses.SOLID) open(shadow?"shadow/solid":"terrain/solid");
        else if(pass==DefaultTerrainRenderPasses.CUTOUT) open(shadow?"shadow/cutout":"terrain/cutout");
        else if(pass==DefaultTerrainRenderPasses.TRANSLUCENT) open(shadow?"shadow/translucent":"terrain/translucent");
        else throw new IllegalStateException("unknown Sodium pass");
    }
    public static void entityFlush(){
        if(active!=null) open(ShadowRenderingState.areShadowsCurrentlyBeingRendered()?"shadow/batched-entities":"main/entities");
    }
    public static void reload(){
        epoch++; names.clear();passNames.clear();selected=null;
        if(active!=null) active.abandoned=true;
    }
}
