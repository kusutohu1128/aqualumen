package dev.aqualumen.profilemixin;

import org.spongepowered.asm.mixin.Mixin;

// The config plugin instruments each target using the same verifier as the offline build.
@Mixin(remap=false,targets={
    "net.minecraft.class_310",
    "net.irisshaders.iris.pipeline.CompositeRenderer",
    "net.irisshaders.iris.shadows.ShadowCompositeRenderer",
    "net.irisshaders.iris.pipeline.FinalPassRenderer",
    "net.irisshaders.iris.pipeline.IrisRenderingPipeline",
    "net.irisshaders.iris.shadows.ShadowRenderer",
    "net.caffeinemc.mods.sodium.client.render.chunk.DefaultChunkRenderer",
    "net.irisshaders.batchedentityrendering.impl.FullyBufferedMultiBufferSource"
})
abstract class Targets {}
