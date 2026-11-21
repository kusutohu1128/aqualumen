package dev.aqualumen.physics;

import java.util.HashSet;
import java.util.Set;

public final class ReceiverRadiancePublisherTest {
    public static void main(String[] args) {
        var epoch = new ReceiverRadianceVolume.Epoch(new Object(), 1, 1);
        var bounds = new ReceiverField.Bounds(0, 0, 0, 1, 1, 1);
        var volume = new ReceiverRadianceVolume(epoch, bounds, new float[] {2,0,0,0}, new float[4], new float[4], new float[4]);
        Set<Integer> live = new HashSet<>();
        int[] calls = {0}, failure = {-1};
        var publisher = new ReceiverRadiancePublisher(new ReceiverRadiancePublisher.Upload() {
            public int create(int width, int height, float[] pixels) {
                if (++calls[0] == failure[0]) throw new IllegalStateException("Injected upload failure");
                if (width != 1 || height != 1 || pixels.length != 4) throw new AssertionError("Wrong upload layout");
                live.add(calls[0]); return calls[0];
            }
            public void delete(int texture) {
                if (!live.remove(texture)) throw new AssertionError("Unowned texture deletion");
            }
        });
        publisher.publish(volume, epoch);
        check(publisher.ready(epoch) == 2 && live.size() == 4, "Atomic positive publication");
        var stale = new ReceiverRadianceVolume.Epoch(epoch.world(), 2, 1);
        check(publisher.ready(stale) == 0 && publisher.texture(0, stale) == 0, "Expired publication");
        failure[0] = 7;
        try { publisher.publish(volume, epoch); throw new AssertionError("Expected upload failure"); }
        catch (IllegalStateException expected) { }
        check(publisher.ready(epoch) == 0 && live.size() == 4, "Partial uploads discarded without exposing old source");
        failure[0] = -1;
        publisher.publish(volume, epoch);
        check(live.size() == 4 && publisher.texture(0, epoch) == 8, "Replacement deletes previous textures");
        publisher.invalidate(); check(publisher.ready(epoch) == 0, "Explicit invalidation");
        publisher.close(); check(live.isEmpty(), "Release all owned textures");
        publisher.close(); check(live.isEmpty(), "Idempotent close");
        System.out.println("ReceiverRadiancePublisher transactional CPU tests passed; no actual GL upload");
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
