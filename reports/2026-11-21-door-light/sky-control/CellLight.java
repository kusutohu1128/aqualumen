package dev.aqualumen.bench;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

/** Client light storage around the measured top faces, after the private Recorder world/UUID guard. */
final class CellLight {
    static long previous;
    static Method light, state;
    static Constructor<?> pos;
    static Object sky, block;

    static void sample(Object client, long now) throws ReflectiveOperationException {
        if (now - previous < 1_000_000_000L) return;
        previous = now;
        Object world = client.getClass().getField("field_1687").get(client);
        if (world == null) return;
        if (pos == null) {
            Class<?> point = Class.forName("net.minecraft.class_2338");
            Class<?> layer = Class.forName("net.minecraft.class_1944");
            pos = point.getConstructor(int.class, int.class, int.class);
            light = Class.forName("net.minecraft.class_1920").getMethod("method_8314", layer, point);
            state = Class.forName("net.minecraft.class_1922").getMethod("method_8320", point);
            sky = layer.getField("field_9284").get(null);
            block = layer.getField("field_9282").get(null);
        }
        Object lamp = state.invoke(world, pos.newInstance(413,163,-404));
        StringBuilder row = new StringBuilder("[HouseCells] ").append(lamp).append(" ");
        for (int z=-403; z<=-398; z++) for (int x=403; x<=408; x++) {
            Object p = pos.newInstance(x,161,z);
            row.append(light.invoke(world,sky,p)).append('/').append(light.invoke(world,block,p)).append(',');
        }
        System.out.println(row);
    }
}
