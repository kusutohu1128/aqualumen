package dev.aqualumen.suntest;

import java.util.function.IntSupplier;
import net.fabricmc.loader.api.FabricLoader;

/** Registers one normal Iris uniform supplier; this class makes no GL calls. */
public final class SunUniforms {
    private SunUniforms() {}
    public static void register(Object holder) {
        try {
            Class<?> frequency=Class.forName("net.irisshaders.iris.gl.uniform.UniformUpdateFrequency");
            Object perFrame=frequency.getField("PER_FRAME").get(null);
            IntSupplier supplier=dev.aqualumen.bench.SunPerformance.wrap(()->SunAuthorization.value(SunAuthorization.runtime(
                FabricLoader.getInstance().getGameDir().toAbsolutePath().normalize())));
            Class.forName("net.irisshaders.iris.gl.uniform.UniformHolder")
                .getMethod("uniform1i",frequency,String.class,IntSupplier.class)
                .invoke(holder,perFrame,"aqualumenSunTestAuthorized",supplier);
        } catch(Exception|LinkageError failure) {
            // An absent/unregistered int uniform remains zero. No exception message or paths.
            System.err.println("[Aqualumen Sun TEST] uniform registration unavailable: "+failure.getClass().getSimpleName());
        }
    }
}
