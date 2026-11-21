package dev.aqualumen.bench.mixin;
import dev.aqualumen.bench.Recorder;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

// Apply after mouse/tick input and before the actual world camera is evaluated.
@Mixin(targets="net.minecraft.class_757", remap=false)
public abstract class CameraMixin {
    @Inject(method="method_3188", at=@At("HEAD"), remap=false)
    private void aqualumenCamera(CallbackInfo callback) { Recorder.beforeWorldRender(); }
    // renderWorld has a single return; restores the F1 flag lifted for a carried-light (lamp-hand-*) world pass.
    @Inject(method="method_3188", at=@At("TAIL"), remap=false)
    private void aqualumenAfterWorld(CallbackInfo callback) { Recorder.afterWorldRender(); }
    // shouldRenderBlockOutline: no selection outline while the carried-light world pass runs with the HUD flag lifted.
    @Inject(method="method_3202", at=@At("HEAD"), cancellable=true, remap=false)
    private void aqualumenOutline(CallbackInfoReturnable<Boolean> callback) { if (Recorder.suppressBlockOutline()) callback.setReturnValue(false); }
}
