package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.ReceiverSodiumIntake;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockRenderer", remap=false)
public abstract class ReceiverSodiumMixin {
    @Inject(method="bufferQuad", at=@At(value="INVOKE", target="Lnet/caffeinemc/mods/sodium/client/render/chunk/vertex/builder/ChunkMeshBufferBuilder;push([Lnet/caffeinemc/mods/sodium/client/render/chunk/vertex/format/ChunkVertexEncoder$Vertex;I)V"), remap=false)
    private void aqualumen$ownedFace(@Coerce Object quad, float[] brightness, @Coerce Object material, CallbackInfo ci) {
        ReceiverSodiumIntake.beforePush(this, quad);
    }
}
