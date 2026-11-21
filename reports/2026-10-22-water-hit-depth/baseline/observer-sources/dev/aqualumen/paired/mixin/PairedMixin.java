package dev.aqualumen.paired.mixin;
import dev.aqualumen.paired.PairedObserver;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(targets="net.irisshaders.iris.pipeline.FinalPassRenderer",remap=false)
public abstract class PairedMixin {
    @Inject(method="renderFinalPass",at=@At(value="INVOKE",target="Lnet/irisshaders/iris/pathways/FullScreenQuadRenderer;renderQuad()V",ordinal=0,shift=At.Shift.BEFORE),remap=false,require=1)
    private void aqualumen$pairedBefore(CallbackInfo info){PairedObserver.before(this);}
    @Inject(method="renderFinalPass",at=@At(value="INVOKE",target="Lnet/irisshaders/iris/pathways/FullScreenQuadRenderer;renderQuad()V",ordinal=0,shift=At.Shift.AFTER),remap=false,require=1)
    private void aqualumen$pairedAfter(CallbackInfo info){PairedObserver.after(this);}
}
