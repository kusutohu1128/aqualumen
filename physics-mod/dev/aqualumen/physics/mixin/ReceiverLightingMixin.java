package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.ReceiverRadianceBridge;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.pipeline.programs.ExtendedShader", remap=false)
public abstract class ReceiverLightingMixin {
    @Inject(method="updateUniforms", at=@At("TAIL"), remap=false)
    private void aqualumen$lightingReady(CallbackInfo ci) {
        ReceiverRadianceBridge.shaderReady();
    }
}
