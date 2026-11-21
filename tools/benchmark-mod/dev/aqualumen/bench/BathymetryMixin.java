package dev.aqualumen.bench.mixin;

import dev.aqualumen.bench.BathymetrySnapshot;
import dev.aqualumen.bench.SolarCacheSnapshot;
import java.util.List;
import java.util.function.Supplier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Pinned Iris 1.8.8 seam; read-only after its actual sampler/uniform updates. */
@Mixin(targets="net.irisshaders.iris.pipeline.programs.SodiumShader",remap=false)
public abstract class BathymetryMixin {
    @Unique private int aqualumen$observedProgram;
    @Unique private String aqualumen$observedPass;
    @Unique private Object aqualumen$observedPipeline;
    @Inject(method="<init>",at=@At("TAIL"),remap=false)
    private void aqualumen$identity(@Coerce Object pipeline,@Coerce Object pass,@Coerce Object bindings,
            int program,@Coerce Object blend,List<?> bufferBlend,@Coerce Object customUniforms,
            Supplier<?> flips,float alphaTest,boolean tessellation,CallbackInfo callback) {
        aqualumen$observedProgram=program;aqualumen$observedPass=String.valueOf(pass);aqualumen$observedPipeline=pipeline;
    }
    @Inject(method="updateUniforms",at=@At("TAIL"),remap=false)
    private void aqualumen$observe(CallbackInfo callback) {
        BathymetrySnapshot.afterSodiumUniforms(aqualumen$observedProgram,aqualumen$observedPass);
    }
    @Inject(method="setupState",at=@At("TAIL"),remap=false)
    private void aqualumen$observeSolarCache(CallbackInfo callback) {
        SolarCacheSnapshot.afterSodiumSetup(aqualumen$observedProgram,aqualumen$observedPass,aqualumen$observedPipeline);
    }
}
