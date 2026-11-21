package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.ReceiverSourceDraw;
import net.irisshaders.iris.gl.shader.GlShader;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets="net.irisshaders.iris.gl.shader.ProgramCreator",remap=false)
public abstract class ReceiverSourceCompileMixin {
    @Inject(method="create",at=@At("RETURN"),remap=false)
    private static void aqualumen$compiled(String name,GlShader[] shaders,CallbackInfoReturnable<Integer> ci) {
        ReceiverSourceDraw.compiled(ci.getReturnValue(),shaders);
    }
}
