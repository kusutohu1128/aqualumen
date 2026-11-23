package dev.aqualumen.idle.mixin;
import dev.aqualumen.idle.Capture;
import net.irisshaders.iris.gl.shader.GlShader;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets="net.irisshaders.iris.gl.shader.ProgramCreator",remap=false)
abstract class LinkMixin {
    @Inject(method="create",at=@At("RETURN"),require=1,allow=1)
    private static void linked(String name, GlShader[] shaders, CallbackInfoReturnable<Integer> ci) {
        Capture.link(name, shaders, ci.getReturnValue());
    }
}
