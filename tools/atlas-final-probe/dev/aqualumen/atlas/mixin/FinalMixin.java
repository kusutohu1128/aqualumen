package dev.aqualumen.atlas.mixin;
import dev.aqualumen.atlas.FinalObserver;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(targets="net.irisshaders.iris.pipeline.FinalPassRenderer",remap=false)
public abstract class FinalMixin {
    @Inject(method="renderFinalPass",at=@At(value="INVOKE",target="Lnet/irisshaders/iris/pathways/FullScreenQuadRenderer;renderQuad()V",shift=At.Shift.BEFORE,ordinal=0),remap=false,require=1)
    private void aqualumen$atlasFinal(CallbackInfo callback){FinalObserver.beforeQuad(this);}
}
