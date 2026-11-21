package dev.aqualumen.atlasjoint.mixin;
import dev.aqualumen.atlasjoint.JointObserver;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(targets="net.irisshaders.iris.pipeline.FinalPassRenderer",remap=false)
public abstract class JointMixin {
    @Inject(method="renderFinalPass",at=@At(value="INVOKE",target="Lnet/irisshaders/iris/pathways/FullScreenQuadRenderer;renderQuad()V",ordinal=0,shift=At.Shift.BEFORE),remap=false,require=1)
    private void aqualumen$jointBefore(CallbackInfo c){JointObserver.before(this);}
    @Inject(method="renderFinalPass",at=@At(value="INVOKE",target="Lnet/irisshaders/iris/pathways/FullScreenQuadRenderer;renderQuad()V",ordinal=0,shift=At.Shift.AFTER),remap=false,require=1)
    private void aqualumen$jointAfter(CallbackInfo c){JointObserver.after(this);}
}
