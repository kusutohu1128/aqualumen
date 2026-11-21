package dev.aqualumen.bench.mixin;

import dev.aqualumen.bench.ShoreRuntimeObserver;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Pinned Iris 1.8.8: final program, samplers and custom uniforms are ready. */
@Mixin(targets="net.irisshaders.iris.pipeline.FinalPassRenderer",remap=false)
public abstract class ShoreFinalMixin {
    @Inject(method="renderFinalPass",at=@At(value="INVOKE",
            target="Lnet/irisshaders/iris/pathways/FullScreenQuadRenderer;renderQuad()V",
            shift=At.Shift.BEFORE,ordinal=0),remap=false,require=1)
    private void aqualumen$observeFinal(CallbackInfo callback) {
        ShoreRuntimeObserver.beforeFinalQuad(this);
    }
}
