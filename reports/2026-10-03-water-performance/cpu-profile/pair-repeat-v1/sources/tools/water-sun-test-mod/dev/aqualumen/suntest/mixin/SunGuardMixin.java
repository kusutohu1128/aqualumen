package dev.aqualumen.suntest.mixin;

import dev.aqualumen.suntest.SunGuardObserver;
import java.util.List;
import java.util.function.Supplier;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets="net.irisshaders.iris.pipeline.programs.SodiumShader",remap=false)
public abstract class SunGuardMixin {
    @Unique private int aqualumenSun$program;
    @Unique private String aqualumenSun$pass;
    @Unique private Object aqualumenSun$pipeline;
    @Unique private boolean aqualumenSun$tessellation;
    @Inject(method="<init>",at=@At("TAIL"),remap=false)
    private void aqualumenSun$identity(@Coerce Object pipeline,@Coerce Object pass,@Coerce Object bindings,
            int program,@Coerce Object blend,List<?> bufferBlend,@Coerce Object customUniforms,
            Supplier<?> flips,float alphaTest,boolean tessellation,CallbackInfo callback) {
        aqualumenSun$program=program;aqualumenSun$pass=String.valueOf(pass);
        aqualumenSun$pipeline=pipeline;aqualumenSun$tessellation=tessellation;
    }
    @Inject(method="updateUniforms",at=@At("TAIL"),remap=false)
    private void aqualumenSun$observe(CallbackInfo callback) {
        SunGuardObserver.afterUniforms(aqualumenSun$program,aqualumenSun$pass,aqualumenSun$tessellation,aqualumenSun$pipeline);
    }
}
