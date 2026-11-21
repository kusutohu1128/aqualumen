package dev.aqualumen.mesherprobe.mixin;

import dev.aqualumen.physics.ReceiverMesherProbe;
import net.irisshaders.iris.gl.uniform.UniformHolder;
import net.irisshaders.iris.shaderpack.IdMap;
import net.irisshaders.iris.shaderpack.properties.PackDirectives;
import net.irisshaders.iris.uniforms.FrameUpdateNotifier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.uniforms.CommonUniforms", remap=false)
public abstract class FrameMixin {
    @Inject(method="addNonDynamicUniforms", at=@At("TAIL"), remap=false)
    private static void aqualumen$frame(UniformHolder holder, IdMap ids, PackDirectives directives,
            FrameUpdateNotifier notifier, CallbackInfo ci) {
        notifier.addListener(ReceiverMesherProbe::frame);
    }
}
