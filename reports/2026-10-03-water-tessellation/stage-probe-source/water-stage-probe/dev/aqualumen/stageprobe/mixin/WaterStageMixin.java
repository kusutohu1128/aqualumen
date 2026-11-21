package dev.aqualumen.stageprobe.mixin;

import dev.aqualumen.stageprobe.WaterStageObserver;
import java.util.List;
import java.util.function.Supplier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Pinned actual Iris 1.8.8 constructor id; SodiumShader does not expose a getHandle method. */
@Mixin(targets="net.irisshaders.iris.pipeline.programs.SodiumShader",remap=false)
public abstract class WaterStageMixin {
    @Unique private int aqualumenStage$program;
    @Unique private String aqualumenStage$pass;
    @Unique private Object aqualumenStage$pipeline;
    @Unique private boolean aqualumenStage$tessellation;
    @Inject(method="<init>",at=@At("TAIL"),remap=false)
    private void aqualumenStage$identity(@Coerce Object pipeline,@Coerce Object pass,@Coerce Object bindings,
            int program,@Coerce Object blend,List<?> bufferBlend,@Coerce Object customUniforms,
            Supplier<?> flips,float alphaTest,boolean tessellation,CallbackInfo callback) {
        aqualumenStage$program=program;aqualumenStage$pass=String.valueOf(pass);
        aqualumenStage$pipeline=pipeline;aqualumenStage$tessellation=tessellation;
    }
    @Inject(method="setupState",at=@At("TAIL"),remap=false)
    private void aqualumenStage$observe(CallbackInfo callback) {
        WaterStageObserver.afterSetup(aqualumenStage$program,aqualumenStage$pass,aqualumenStage$tessellation,aqualumenStage$pipeline);
    }
}
