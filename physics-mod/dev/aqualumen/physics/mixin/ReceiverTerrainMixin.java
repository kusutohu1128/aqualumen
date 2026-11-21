package dev.aqualumen.physics.mixin;

import dev.aqualumen.physics.ReceiverRadianceBridge;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.caffeinemc.mods.sodium.client.gl.device.GLRenderDevice$ImmediateDrawCommandList",remap=false)
public abstract class ReceiverTerrainMixin {
    @Inject(method="multiDrawElementsBaseVertex",at=@At("HEAD"),remap=false)
    private void aqualumen$terrainReady(@Coerce Object batch,@Coerce Object index,CallbackInfo ci) {
        ReceiverRadianceBridge.terrainReady();
    }
    @Inject(method="multiDrawElementsBaseVertex",at=@At("RETURN"),remap=false)
    private void aqualumen$terrainFinished(@Coerce Object batch,@Coerce Object index,CallbackInfo ci) {
        ReceiverRadianceBridge.terrainFinished();
    }
}
