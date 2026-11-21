package dev.aqualumen.drawprobe.mixin;
import dev.aqualumen.drawprobe.ReceiverDrawProbe;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(targets="net.caffeinemc.mods.sodium.client.gl.device.GLRenderDevice$ImmediateDrawCommandList", remap=false)
public abstract class DrawMixin {
    @Inject(method="multiDrawElementsBaseVertex", at=@At("HEAD"), remap=false)
    private void aqualumen$before(@Coerce Object batch, @Coerce Object index, CallbackInfo ci) { ReceiverDrawProbe.beforeDraw(batch); }
    @Inject(method="multiDrawElementsBaseVertex", at=@At("RETURN"), remap=false)
    private void aqualumen$after(@Coerce Object batch, @Coerce Object index, CallbackInfo ci) { ReceiverDrawProbe.afterDraw(); }
}
