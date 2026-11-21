package dev.aqualumen.physics;

import java.util.List;

public final class ReceiverWaterVolumeTest {
    private static ReceiverWaterVolume.Observation observation(String id, float height, boolean water, boolean clear) {
        return new ReceiverWaterVolume.Observation(true,id,id,water,height,clear);
    }
    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
    public static void main(String[] arguments) throws Exception {
        var water = observation("minecraft:water",1,true,true);
        for (String id : List.of("minecraft:seagrass","minecraft:tall_seagrass","minecraft:kelp","minecraft:kelp_plant")) {
            var plant = observation(id,1,true,true);
            check(plant.full() && ReceiverWaterVolume.fullColumn(List.of(plant,water,water)),"Continuous full fluid with exact supported plant ID");
            check(ReceiverField.classifyVanilla(id,true,false,true,false).kind() == ReceiverField.Kind.UNSUPPORTED,
                    "Fluid proof does not reclassify visible plant geometry as empty water");
        }
        for (var invalid : List.of(observation("minecraft:water",.875f,true,true),observation("minecraft:kelp",1,false,true),
                observation("minecraft:kelp",1,true,false),observation("minecraft:oak_fence",1,true,true),
                observation("minecraft:water",Float.NaN,true,true),observation("minecraft:water",Float.POSITIVE_INFINITY,true,true),
                new ReceiverWaterVolume.Observation(false,"minecraft:water","water",true,1,true),
                new ReceiverWaterVolume.Observation(true,"minecraft:water","",true,1,true))) {
            check(!invalid.full() && !ReceiverWaterVolume.fullColumn(List.of(water,invalid,water)),"Unavailable/partial/wrong-fluid/collision/identity negatives");
        }
        check(!ReceiverWaterVolume.fullColumn(List.of(water,water)),"Three-cell depth proof required");
        Object retained = new Object(); Object[] current = {retained}; int[] reads = {0};
        var lease = new ReceiverChunkLease<>((sectionX,sectionZ) -> {
            check(sectionX == -1 && sectionZ == 1,"Negative world-to-section mapping");
            reads[0]++; return current[0];
        });
        check(lease.existing(-1,16) == retained && lease.existing(-16,31) == retained && reads[0] == 1,"Retained pointer cached during collection");
        lease.validate(); check(reads[0] == 2,"Validation fresh-reads already-present chunk pointer");
        current[0] = new Object();
        rejected(lease::validate); current[0] = null; rejected(lease::validate);
        var isolated = new java.util.concurrent.atomic.AtomicBoolean();
        Thread other = new Thread(() -> {
            try { lease.validate(); } catch (IllegalStateException expected) { isolated.set(true); }
            catch (ReflectiveOperationException unexpected) { throw new AssertionError(unexpected); }
        });
        int before = reads[0]; other.start(); other.join();
        check(isolated.get() && reads[0] == before,"Foreign thread rejected before backend lookup");
        Object[] absent = {null};
        var unavailable = new ReceiverChunkLease<>((sectionX,sectionZ) -> absent[0]);
        check(unavailable.existing(0,0) == null,"Unavailable chunk remains unavailable");
        unavailable.validate(); absent[0] = retained; rejected(unavailable::validate);
        String original = new String("same"); String[] equal = {original};
        var identity = new ReceiverChunkLease<>((sectionX,sectionZ) -> equal[0]);
        identity.existing(0,0); equal[0] = new String("same"); rejected(identity::validate);
        boolean[] failure = {false};
        var failing = new ReceiverChunkLease<>((sectionX,sectionZ) -> {
            if (failure[0]) throw new ReflectiveOperationException("Existing chunk lookup unavailable");
            return retained;
        });
        failing.existing(0,0); failure[0] = true;
        try {
            failing.validate(); throw new AssertionError("Backend failure treated as current chunk");
        } catch (ReflectiveOperationException expected) {}
        System.out.println("PASS fluid-volume CPU: full supported plant water, partial/collision/identity negatives; chunk pointer fresh validation, unload/replacement/null transition/thread guards; not live unload or plant DDA acceptance");
    }
    private static void rejected(Action action) throws ReflectiveOperationException {
        try { action.run(); throw new AssertionError("Changed chunk lease admitted"); }
        catch (IllegalStateException expected) {}
    }
    @FunctionalInterface private interface Action { void run() throws ReflectiveOperationException; }
}
