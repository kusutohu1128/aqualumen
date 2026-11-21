package dev.aqualumen.physics;

import java.util.HashMap;
import java.util.Objects;

public final class ReceiverChunkLease<Value> {
    @FunctionalInterface
    public interface Lookup<Value> { Value existing(int sectionX, int sectionZ) throws ReflectiveOperationException; }
    private record Section(int x, int z) {}
    private final Thread owner = Thread.currentThread();
    private final Lookup<Value> lookup;
    private final HashMap<Section,Value> retained = new HashMap<>();
    public ReceiverChunkLease(Lookup<Value> lookup) { this.lookup = Objects.requireNonNull(lookup); }
    public Value existing(int worldX, int worldZ) throws ReflectiveOperationException {
        owner();
        var section = new Section(Math.floorDiv(worldX,16),Math.floorDiv(worldZ,16));
        if (!retained.containsKey(section)) retained.put(section,lookup.existing(section.x(),section.z()));
        return retained.get(section);
    }
    public void validate() throws ReflectiveOperationException {
        owner();
        for (var entry : retained.entrySet()) {
            var section = entry.getKey();
            if (lookup.existing(section.x(),section.z()) != entry.getValue())
                throw new IllegalStateException("Loaded receiver chunk identity changed before publication");
        }
    }
    private void owner() {
        if (Thread.currentThread() != owner) throw new IllegalStateException("Receiver chunk lease outside owner");
    }
}
