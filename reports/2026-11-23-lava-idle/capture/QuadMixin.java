package dev.aqualumen.idle.mixin;
import dev.aqualumen.idle.Capture;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.pathways.FullScreenQuadRenderer",remap=false)
abstract class QuadMixin {
    @Inject(method="renderQuad",at=@At("HEAD"),require=1,allow=1)
    private void draw(CallbackInfo ci) { Capture.draw(); }
}
