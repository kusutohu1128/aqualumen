package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.Bathymetry;
import dev.aqualumen.physics.ReceiverRadianceBridge;
import net.irisshaders.iris.gl.sampler.SamplerHolder;
import net.irisshaders.iris.pipeline.WorldRenderingPipeline;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.samplers.IrisSamplers",remap=false)
public abstract class SamplerMixin {
    @Inject(method="addLevelSamplers",at=@At("TAIL"),remap=false)
    private static void aqualumen$bathymetry(SamplerHolder holder,WorldRenderingPipeline pipeline,
            @Coerce Object texture,boolean a,boolean b,boolean c,CallbackInfo ci) {
        if(holder.hasSampler("aqualumenBathymetry"))
            holder.addDynamicSampler(Bathymetry::textureId,"aqualumenBathymetry");
        ReceiverRadianceBridge.register(holder);
    }
}
