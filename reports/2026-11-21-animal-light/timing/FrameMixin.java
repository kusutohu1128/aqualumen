package dev.aqualumen.animalqa.mixin;
import dev.aqualumen.animalqa.FrameSample;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.minecraft.class_310",remap=false)
public abstract class FrameMixin {
    @Inject(method="method_1523",at=@At("TAIL"),remap=false)
    private void recordReturn(CallbackInfo callback) { FrameSample.record(this); }
}
