package dev.aqualumen.mesherprobe.mixin;

import dev.aqualumen.physics.ReceiverMesherProbe;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockRenderer", remap=false)
public abstract class MesherMixin {
    @Inject(method="bufferQuad", at=@At("HEAD"), remap=false)
    private void aqualumen$clear(@Coerce Object quad, float[] brightness, @Coerce Object material, CallbackInfo ci) {
        ReceiverMesherProbe.clearQuad();
    }
    @Inject(method="bufferQuad", at=@At(value="INVOKE", target="Lnet/caffeinemc/mods/sodium/client/render/chunk/vertex/builder/ChunkMeshBufferBuilder;push([Lnet/caffeinemc/mods/sodium/client/render/chunk/vertex/format/ChunkVertexEncoder$Vertex;I)V"), remap=false)
    private void aqualumen$capture(@Coerce Object quad, float[] brightness, @Coerce Object material, CallbackInfo ci) {
        ReceiverMesherProbe.beforePush(this, quad);
    }
    @Inject(method="bufferQuad", at=@At("RETURN"), remap=false)
    private void aqualumen$end(@Coerce Object quad, float[] brightness, @Coerce Object material, CallbackInfo ci) {
        ReceiverMesherProbe.clearQuad();
    }
}
