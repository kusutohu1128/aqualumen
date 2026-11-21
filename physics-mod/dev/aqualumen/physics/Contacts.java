package dev.aqualumen.physics;

import net.fabricmc.loader.api.FabricLoader;
import net.irisshaders.iris.gl.uniform.UniformHolder;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.gl.uniform.UniformUpdateFrequency;
import net.irisshaders.iris.uniforms.CameraUniforms;
import net.irisshaders.iris.uniforms.FrameUpdateNotifier;
import net.irisshaders.iris.uniforms.SystemTimeUniforms;
import org.joml.Vector3d;
import org.joml.Vector4f;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** Version-pinned read-only Minecraft bridge. Never sends commands or changes blocks/entities. */
public final class Contacts {
    private static final Vector4f grid=new Vector4f(0,0,64,0), shift=new Vector4f();
    private static final Vector4f[] sources=new Vector4f[8];
    private static final Map<Object, double[]> positions=new WeakHashMap<>();
    private static long previous,lastStatus,lastContact,lastPlaneProbe;
    private static int lastFrame=-1;
    private static double originX,originZ,plane=63;
    private static float dt;
    private static int active,dimension,contacts,resets;
    private static Object oldWorld;
    private static boolean initialized,failed;
    private static Object mc,stillWater,flowingWater;
    private static Field worldField;
    private static Method entities,x,y,z,touching,lava,spectator,type,fluid,fluidKind,fluidHeight,registry,keyValue,paused;
    private static Constructor<?> blockPos;
    static { for(int i=0;i<sources.length;i++) sources[i]=new Vector4f(); }

    public static void register(UniformHolder h,FrameUpdateNotifier notifier) {
        // One snapshot shared by every program; some Iris pipelines create multiple notifiers.
        notifier.addListener(Contacts::update);
        var f=UniformUpdateFrequency.PER_FRAME;
        h.uniform4f(f,"aqualumenGrid",()->grid);
        h.uniform4f(f,"aqualumenShift",()->shift);
        h.uniform1f(f,"aqualumenDelta",()->dt);
        h.uniform1i(f,"aqualumenActive",()->active);
        h.uniform1i(f,"aqualumenDimension",()->dimension);
        for(int i=0;i<sources.length;i++) {
            final int index=i;
            h.uniform4f(f,"aqualumenContact"+i,()->sources[index]);
        }
    }
    private static void init() throws Exception {
        Class<?> client=Class.forName("net.minecraft.class_310");
        mc=client.getMethod("method_1551").invoke(null);
        worldField=client.getField("field_1687");paused=client.getMethod("method_1493");
        Class<?> entity=Class.forName("net.minecraft.class_1297");
        x=entity.getMethod("method_23317");y=entity.getMethod("method_23318");z=entity.getMethod("method_23321");
        touching=entity.getMethod("method_5799");lava=entity.getMethod("method_5771");
        spectator=entity.getMethod("method_7325");type=entity.getMethod("method_5864");
        entities=Class.forName("net.minecraft.class_638").getMethod("method_18112");
        Class<?> pos=Class.forName("net.minecraft.class_2338");blockPos=pos.getConstructor(int.class,int.class,int.class);
        fluid=Class.forName("net.minecraft.class_1937").getMethod("method_8316",pos);
        Class<?> state=Class.forName("net.minecraft.class_3610");
        fluidKind=state.getMethod("method_15772");fluidHeight=state.getMethod("method_20785");
        Class<?> fluids=Class.forName("net.minecraft.class_3612");
        stillWater=fluids.getField("field_15910").get(null);flowingWater=fluids.getField("field_15909").get(null);
        registry=Class.forName("net.minecraft.class_1937").getMethod("method_27983");
        keyValue=Class.forName("net.minecraft.class_5321").getMethod("method_29177");
        initialized=true;
        System.out.println("[Aqualumen Physics] 0.3.0 candidate contact + loaded-column bathymetry bridge initialized");
    }
    private static double surface(Object world,double ex,double ey,double ez) throws Exception {
        // Find nearby WATER first, then follow that contiguous column, never an unrelated upper pool.
        int bx=(int)Math.floor(ex),bz=(int)Math.floor(ez);
        LoadedWorld loaded=new LoadedWorld(world);
        if(!loaded.loaded(bx,bz)) return Double.NaN;
        int base=(int)Math.floor(ey);
        for(int radius=0;radius<=3;radius++) for(int sign:new int[]{-1,1}) {
            int by=base+radius*sign;
            if(by<loaded.minY() || by>=loaded.maxY()) continue;
            var state=loaded.cell(bx,by,bz);
            if(!state.water()) continue;
            for(int steps=0;steps<32;steps++) {
                if(by+1>=loaded.maxY()) return Double.NaN;
                var above=loaded.cell(bx,by+1,bz);
                if(!above.water()) return by+state.height();
                state=above;by++;
            }
            return Double.NaN; // Surface too distant; don't invent a local water plane.
        }
        return Double.NaN;
    }
    static void ensureUpdate() {update();}
    static Object currentWorld() {return failed?null:oldWorld;}
    static double referenceSurface() {return plane;}
    static int currentDimension() {return dimension;}
    private static boolean water(Object state) throws Exception {
        Object kind=fluidKind.invoke(state);return kind==stillWater || kind==flowingWater;
    }
    private static void update() {
        int frame=SystemTimeUniforms.COUNTER.getAsInt();
        if(failed || frame==lastFrame) return;
        long now=System.nanoTime();
        lastFrame=frame;
        if(!Iris.isPackInUseQuick() || !Iris.getCurrentPackName().startsWith("Aqualumen")) {active=0;dt=0;oldWorld=null;return;}
        try {
            if(!initialized) init();
            Object world=worldField.get(mc);
            double elapsed=previous==0?0:(now-previous)*1e-9;previous=now;
            dt=(boolean)paused.invoke(mc)?0:(float)Math.min(Math.max(elapsed,0),0.05);
            for(var source:sources) source.zero();
            contacts=0;
            if(world==null) {active=0;oldWorld=null;return;}
            String id=keyValue.invoke(registry.invoke(world)).toString();
            dimension=id.equals("minecraft:the_nether")?-1:id.equals("minecraft:the_end")?1:0;
            Vector3d camera=CameraUniforms.getUnshiftedCameraPosition();
            double nextX=Math.floor((camera.x-32)/0.125)*0.125;
            double nextZ=Math.floor((camera.z-32)/0.125)*0.125;
            double oldPlane=plane;
            boolean reset=oldWorld!=world;
            if(reset) { positions.clear(); lastContact=0;plane=63; }
            // Nearest real moving water-contact entity chooses the local water plane.
            var candidates=new ArrayList<Object>();
            for(Object e:(Iterable<?>)entities.invoke(world)) {
                if(!(boolean)touching.invoke(e) || (boolean)lava.invoke(e) || (boolean)spectator.invoke(e)) continue;
                double ex=(double)x.invoke(e),ez=(double)z.invoke(e);
                if(Math.abs(ex-camera.x)<29 && Math.abs(ez-camera.z)<29) candidates.add(e);
            }
            candidates.sort(Comparator.comparingDouble(e->{try{return Math.hypot((double)x.invoke(e)-camera.x,(double)z.invoke(e)-camera.z);}catch(Exception ignored){return 1e9;}}));
            for(Object e:candidates) {
                double ex=(double)x.invoke(e),ey=(double)y.invoke(e),ez=(double)z.invoke(e);
                double height=surface(world,ex,ey,ez);
                if(!Double.isFinite(height)) continue;
                if(contacts==0) plane=height;
                if(Math.abs(height-plane)>0.5) continue;
                double[] old=positions.get(e);
                double speed=0,vertical=0;
                if(old==null) positions.put(e,new double[]{ex,ey,ez,now*1e-9,0,0});
                else if(Math.abs(ex-old[0])+Math.abs(ey-old[1])+Math.abs(ez-old[2])>0.00001) {
                    double seconds=Math.max(now*1e-9-old[3],0.01);
                    speed=Math.min(12,Math.hypot(ex-old[0],ez-old[2])/seconds);
                    vertical=Math.min(6,Math.abs(ey-old[1])/seconds);
                    positions.put(e,new double[]{ex,ey,ez,now*1e-9,speed,vertical});
                } else {
                    double decay=Math.exp(-Math.max(now*1e-9-old[3]-0.06,0)/0.10);
                    speed=old[4]*decay;vertical=old[5]*decay;
                }
                String entityType=type.invoke(e).toString();
                boolean boat=entityType.contains("boat");
                float force=(float)Math.min(8,speed*(boat?1.5:0.8)+vertical*0.5);
                sources[contacts++].set((float)(ex-camera.x),(float)(ez-camera.z),force,boat?0.65f:0.30f);
                lastContact=now;
                if(contacts==8) break;
            }
            // Keep the physical plane alive without a moving source, including underwater views.
            // Probe only 5Hz; it is read-only and does not request/generate distant chunks.
            if(contacts==0 && now-lastPlaneProbe>200_000_000L) {
                lastPlaneProbe=now;
                double height=surface(world,camera.x,camera.y,camera.z);
                if(Double.isFinite(height)) {plane=height;lastContact=now;}
            }
            reset |= Math.abs(plane-oldPlane)>0.5 || Math.abs(nextX-originX)>16 || Math.abs(nextZ-originZ)>16;
            shift.set((float)((nextX-originX)/0.125),(float)((nextZ-originZ)/0.125),reset?1:0,0);
            if(reset) resets++;
            originX=nextX;originZ=nextZ;oldWorld=world;
            grid.set((float)(originX-camera.x),(float)(originZ-camera.z),64,(float)(plane-camera.y));
            active=dimension==0 && now-lastContact<10_000_000_000L?1:0;
            if(now-lastStatus>1_000_000_000L) {
                lastStatus=now;
                Path status=FabricLoader.getInstance().getGameDir().resolve("config/aqualumen-physics-status.json");
                String json=String.format(Locale.ROOT,"{\"version\":\"0.3.0-candidate\",\"active\":%d,\"dimension\":%d,\"contacts\":%d,\"max_force\":%.4f,\"delta_seconds\":%.6f,\"surface_y\":%.4f,\"resets\":%d,\"resolution\":512,\"span_metres\":64,\"solver\":\"linear-wave-height\",%s}\n",active,dimension,contacts,Arrays.stream(sources).mapToDouble(v->v.z).max().orElse(0),dt,plane,resets,Bathymetry.statusFields());
                Files.writeString(status,json);
            }
        } catch(Exception error) {
            failed=true;active=0;dt=0;
            System.err.println("[Aqualumen Physics] Disabled safely: "+error);error.printStackTrace();
        }
    }
}
