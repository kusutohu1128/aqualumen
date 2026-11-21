package dev.aqualumen.physics;

import java.lang.reflect.Method;
import java.nio.*;
import java.util.Locale;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.gl.uniform.*;
import net.irisshaders.iris.uniforms.*;
import org.joml.Vector3d;
import org.joml.Vector4f;
import org.lwjgl.opengl.*;

/** One bounded, render-thread world snapshot shared by vertex and fragment programs. */
public final class Bathymetry {
    private static final BathymetryField field=new BathymetryField();
    private static final Vector4f grid=new Vector4f(0,0,64,0);
    private static final FloatBuffer pixels=ByteBuffer.allocateDirect(64*64*4*Float.BYTES)
            .order(ByteOrder.nativeOrder()).asFloatBuffer();
    private static int texture,lastFrame=Integer.MIN_VALUE,ready,known,scanned,uploadCalls;
    private static long updateNanos;
    private static boolean invalidate=true,failed;
    private static Method renderThread;

    public static void register(UniformHolder holder,FrameUpdateNotifier notifier) {
        invalidate=true; // Pack/pipeline reload must never reuse old validity.
        notifier.addListener(Bathymetry::update);
        holder.uniform4f(UniformUpdateFrequency.PER_FRAME,"aqualumenBathymetryGrid",()->{update();return grid;});
        holder.uniform1i(UniformUpdateFrequency.PER_FRAME,"aqualumenBathymetryReady",()->{update();return ready;});
    }
    public static int textureId() {
        update(); // Sodium updates samplers before uniforms; this must establish the same snapshot.
        return texture;
    }
    static String statusFields() {
        // Contacts' 1Hz status writer may report the preceding frame; expose that frame explicitly.
        return String.format(Locale.ROOT,"\"bathymetry\":{\"ready\":%d,\"known_columns\":%d,\"scanned_columns\":%d,\"frame\":%d,\"cpu_update_ms\":%.4f,\"texture_id\":%d,\"upload_calls\":%d,\"failed\":%s}",
                ready,known,scanned,lastFrame,updateNanos*1e-6,texture,uploadCalls,failed);
    }
    private static boolean onRenderThread() throws ReflectiveOperationException {
        if(renderThread==null) renderThread=Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread");
        return (boolean)renderThread.invoke(null);
    }
    private static void update() {
        if(failed) return;
        int frame=SystemTimeUniforms.COUNTER.getAsInt();
        // Registration may occur lazily during a frame. Defer its invalidation to the next
        // frame so no program observes a different field between vertex/fragment draws.
        if(frame==lastFrame) return;
        long started=System.nanoTime();
        try {
            if(!onRenderThread()) {ready=0;return;}
            lastFrame=frame;
            if(invalidate) {field.reset();invalidate=false;ready=0;}
            Contacts.ensureUpdate();
            Object world=Contacts.currentWorld();
            Vector3d camera=CameraUniforms.getUnshiftedCameraPosition();
            double reference=Contacts.referenceSurface();
            pixels.clear();ready=0;known=0;scanned=0;
            if(Iris.isPackInUseQuick() && Iris.getCurrentPackName().startsWith("Aqualumen")
                    && world!=null && Contacts.currentDimension()==0 && Double.isFinite(reference)
                    && Double.isFinite(camera.x) && Double.isFinite(camera.y) && Double.isFinite(camera.z)
                    && Math.abs(camera.x)<30_000_001 && Math.abs(camera.z)<30_000_001
                    && Float.isFinite((float)camera.y)) {
                int x=(int)Math.floor(camera.x)-32,z=(int)Math.floor(camera.z)-32;
                var snapshot=field.update(new LoadedWorld(world),world,x,z,reference,16);
                scanned=snapshot.scanned;
                grid.set((float)(x-camera.x),(float)(z-camera.z),64,(float)(reference-camera.y));
                for(int j=0;j<64;j++) for(int i=0;i<64;i++) {
                    var column=snapshot.columnAt(x+i,z+j);
                    if(column.valid()) {
                        pixels.put(column.depth()).put((float)(column.surface()-camera.y)).put(1).put(0);ready=1;known++;
                    } else pixels.put(0).put(0).put(0).put(0);
                }
            } else {
                field.reset();grid.set(0,0,64,0);
                while(pixels.hasRemaining()) pixels.put(0);
            }
            pixels.flip();upload();uploadCalls++;
        } catch(Exception error) {
            failed=true;ready=0;known=0;field.reset();
            System.err.println("[Aqualumen Physics] Bathymetry disabled safely: "+error);
            error.printStackTrace();
        } finally {
            updateNanos=System.nanoTime()-started;
        }
    }
    private static void upload() {
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        int binding=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
        int unpack=GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING);
        int alignment=GL11.glGetInteger(GL11.GL_UNPACK_ALIGNMENT);
        int rowLength=GL11.glGetInteger(GL11.GL_UNPACK_ROW_LENGTH);
        int skipRows=GL11.glGetInteger(GL11.GL_UNPACK_SKIP_ROWS);
        int skipPixels=GL11.glGetInteger(GL11.GL_UNPACK_SKIP_PIXELS);
        int swapBytes=GL11.glGetInteger(GL11.GL_UNPACK_SWAP_BYTES);
        try {
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER,0);
            GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT,4);
            GL11.glPixelStorei(GL11.GL_UNPACK_ROW_LENGTH,0);
            GL11.glPixelStorei(GL11.GL_UNPACK_SKIP_ROWS,0);
            GL11.glPixelStorei(GL11.GL_UNPACK_SKIP_PIXELS,0);
            GL11.glPixelStorei(GL11.GL_UNPACK_SWAP_BYTES,GL11.GL_FALSE);
            if(texture==0) {
                texture=GL11.glGenTextures();GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
                GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER,GL11.GL_NEAREST);
                GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER,GL11.GL_NEAREST);
                GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_WRAP_S,GL12.GL_CLAMP_TO_EDGE);
                GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_WRAP_T,GL12.GL_CLAMP_TO_EDGE);
                GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL30.GL_RGBA32F,64,64,0,GL11.GL_RGBA,GL11.GL_FLOAT,pixels);
            } else {
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
                GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,0,64,64,GL11.GL_RGBA,GL11.GL_FLOAT,pixels);
            }
        } finally {
            GL13.glActiveTexture(active);GL11.glBindTexture(GL11.GL_TEXTURE_2D,binding);
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER,unpack);
            GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT,alignment);
            GL11.glPixelStorei(GL11.GL_UNPACK_ROW_LENGTH,rowLength);
            GL11.glPixelStorei(GL11.GL_UNPACK_SKIP_ROWS,skipRows);
            GL11.glPixelStorei(GL11.GL_UNPACK_SKIP_PIXELS,skipPixels);
            GL11.glPixelStorei(GL11.GL_UNPACK_SWAP_BYTES,swapBytes);
        }
    }
}
