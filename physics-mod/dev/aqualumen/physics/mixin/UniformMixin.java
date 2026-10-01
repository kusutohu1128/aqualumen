package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.Contacts;
import net.irisshaders.iris.gl.uniform.UniformHolder;
import net.irisshaders.iris.shaderpack.IdMap;
import net.irisshaders.iris.shaderpack.properties.PackDirectives;
import net.irisshaders.iris.uniforms.FrameUpdateNotifier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.uniforms.CommonUniforms", remap=false)
public abstract class UniformMixin {
    @Inject(method="addNonDynamicUniforms", at=@At("TAIL"), remap=false)
    private static void aqualumen$contacts(UniformHolder holder, IdMap ids,
            PackDirectives directives, FrameUpdateNotifier notifier, CallbackInfo ci) {
        Contacts.register(holder, notifier);
    }
}
