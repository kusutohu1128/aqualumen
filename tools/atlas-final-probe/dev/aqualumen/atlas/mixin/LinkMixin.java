package dev.aqualumen.atlas.mixin;
import dev.aqualumen.atlas.FinalObserver;
import net.irisshaders.iris.gl.shader.GlShader;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
@Mixin(targets="net.irisshaders.iris.gl.shader.ProgramCreator",remap=false)
public abstract class LinkMixin {
    @Inject(method="create",at=@At("RETURN"),remap=false,require=1)
    private static void aqualumen$linked(String name,GlShader[] shaders,CallbackInfoReturnable<Integer> callback){FinalObserver.linked(name,shaders,callback.getReturnValue());}
}
