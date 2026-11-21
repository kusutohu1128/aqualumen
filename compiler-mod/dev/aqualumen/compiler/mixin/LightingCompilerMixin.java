package dev.aqualumen.compiler.mixin;

import dev.aqualumen.compiler.LightingCompiler;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Mixin(targets = {
    "net.irisshaders.iris.gl.shader.ShaderWorkarounds",
    "net.caffeinemc.mods.sodium.client.gl.shader.ShaderWorkarounds"
}, remap = false)
abstract class LightingCompilerMixin {
    @ModifyVariable(method = "safeShaderSource(ILjava/lang/CharSequence;)V",
            at = @At("HEAD"), argsOnly = true, index = 1)
    private static CharSequence aqualumen$compileLighting(CharSequence shader) {
        return LightingCompiler.prepare(shader.toString(), false);
    }
}
