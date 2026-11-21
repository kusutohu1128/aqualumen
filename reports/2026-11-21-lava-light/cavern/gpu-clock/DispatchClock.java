package dev.aqualumen.privateclock.mixin;

import java.nio.file.Path;
import org.lwjgl.opengl.GL15;
import org.lwjgl.opengl.GL20;
import org.lwjgl.opengl.GL33;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Two asynchronous timestamps per sample. The measured program is never suspended for readback. */
@Mixin(targets="net.irisshaders.iris.gl.program.ComputeProgram",remap=false)
abstract class DispatchClock {
    @Shadow public abstract int getProgramId();
    @Unique private int aqlStart, aqlEnd, aqlFrame;
    @Unique private boolean aqlSample, aqlPending;
    @Unique private String aqlName;

    @Inject(method="dispatch(FF)V", at=@At("HEAD"))
    private void aqlBegin(float width,float height,CallbackInfo info) {
        if (aqlName == null) {
            Path game=Path.of("").toAbsolutePath();
            if (!game.getFileName().toString().equals("minecraft")
                || !game.getParent().getFileName().toString().startsWith("aql-cavern-")) {
                aqlName="disabled";
                return;
            }
            int id=getProgramId();
            aqlName="other-"+id;
            for (String key:new String[]{"bounceIncidentImage","bounceExitImage","lampListImage","shoreFaceImage"})
                if (GL20.glGetUniformLocation(id,key)>=0) { aqlName=key; break; }
            aqlStart=GL15.glGenQueries();
            aqlEnd=GL15.glGenQueries();
        }
        if (aqlStart==0) return;
        if (aqlPending && GL15.glGetQueryObjecti(aqlEnd,GL15.GL_QUERY_RESULT_AVAILABLE)!=0) {
            long dt=GL33.glGetQueryObjectui64(aqlEnd,GL15.GL_QUERY_RESULT)
                    -GL33.glGetQueryObjectui64(aqlStart,GL15.GL_QUERY_RESULT);
            if (aqlFrame<=600) System.out.println("[PrivateGPU] "+aqlName+" "+aqlFrame+" "+dt);
            aqlPending=false;
        }
        aqlSample=!aqlPending && (++aqlFrame%7==1) && aqlFrame<600;
        if (aqlSample) GL33.glQueryCounter(aqlStart,GL33.GL_TIMESTAMP);
    }
    @Inject(method="dispatch(FF)V", at=@At("RETURN"))
    private void aqlFinish(float width,float height,CallbackInfo info) {
        if (aqlSample) { GL33.glQueryCounter(aqlEnd,GL33.GL_TIMESTAMP); aqlPending=true; }
    }
}
