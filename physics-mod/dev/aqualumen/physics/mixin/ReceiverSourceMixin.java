package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.ReceiverRadianceBridge;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.gl.program.Program", remap=false)
public abstract class ReceiverSourceMixin {
    @Inject(method="use", at=@At("TAIL"), remap=false)
    private void aqualumen$sourceReady(CallbackInfo ci) {
        ReceiverRadianceBridge.sourceReady();
    }
}
