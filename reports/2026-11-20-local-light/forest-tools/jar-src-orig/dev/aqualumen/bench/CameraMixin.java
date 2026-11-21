package dev.aqualumen.bench.mixin;
import dev.aqualumen.bench.Recorder;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

// Apply after mouse/tick input and before the actual world camera is evaluated.
@Mixin(targets="net.minecraft.class_757", remap=false)
public abstract class CameraMixin {
    @Inject(method="method_3188", at=@At("HEAD"), remap=false)
    private void aqualumenCamera(CallbackInfo callback) { Recorder.beforeWorldRender(); }
}
