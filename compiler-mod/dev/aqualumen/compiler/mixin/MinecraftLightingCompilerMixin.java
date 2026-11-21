package dev.aqualumen.compiler.mixin;

import dev.aqualumen.compiler.LightingCompiler;

import java.util.List;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Mixin(targets = "com.mojang.blaze3d.platform.GlStateManager", remap = false)
abstract class MinecraftLightingCompilerMixin {
    @ModifyVariable(method = "glShaderSource(ILjava/util/List;)V", at = @At("HEAD"), argsOnly = true, index = 1)
    private static List<String> aqualumen$compileLighting(List<String> chunks) {
        // Minecraft concatenates these strings verbatim before handing them to OpenGL.
        // Most vanilla and other-pack programs never need a second source allocation.
        if (chunks.stream().noneMatch(s -> s.contains("aqualumenAreaSourceLighting"))) return chunks;
        String source = String.join("", chunks);
        String prepared = LightingCompiler.prepare(source, true);
        return prepared == source ? chunks : List.of(prepared);
    }
}
