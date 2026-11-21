package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;
import java.util.Set;

public final class ReceiverWaterVolume {
    private static final Set<String> plants = Set.of("minecraft:seagrass","minecraft:tall_seagrass","minecraft:kelp","minecraft:kelp_plant");
    public record Observation(boolean loaded, String blockId, String state, boolean water,
                              float height, boolean emptyCollision) {
        public Observation { Objects.requireNonNull(blockId); Objects.requireNonNull(state); }
        public boolean full() {
            return loaded && water && Float.isFinite(height) && height == 1 && emptyCollision
                    && !state.isEmpty() && (blockId.equals("minecraft:water") || plants.contains(blockId));
        }
    }
    private ReceiverWaterVolume() {}
    public static boolean fullColumn(List<Observation> observations) {
        var owned = List.copyOf(observations);
        return owned.size() == 3 && owned.stream().allMatch(Observation::full);
    }
}
