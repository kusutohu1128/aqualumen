package dev.aqualumen.mesherprobe.mixin;

import dev.aqualumen.physics.ReceiverMesherProbe;
import net.caffeinemc.mods.sodium.client.render.chunk.vertex.format.ChunkVertexEncoder.Vertex;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets="net.irisshaders.iris.vertices.sodium.terrain.XHFPTerrainVertex", remap=false)
public abstract class EncoderMixin {
    @Shadow private int stride;
    @Inject(method="write", at=@At("HEAD"), remap=false)
    private void aqualumen$begin(long pointer, int material, Vertex[] vertices, int section, CallbackInfoReturnable<Long> ci) {
        ReceiverMesherProbe.beginWrite(pointer, stride, material, vertices, section);
    }
    @Inject(method="write", at=@At("RETURN"), remap=false)
    private void aqualumen$end(long pointer, int material, Vertex[] vertices, int section, CallbackInfoReturnable<Long> ci) {
        ReceiverMesherProbe.endWrite(ci.getReturnValue());
    }
}
