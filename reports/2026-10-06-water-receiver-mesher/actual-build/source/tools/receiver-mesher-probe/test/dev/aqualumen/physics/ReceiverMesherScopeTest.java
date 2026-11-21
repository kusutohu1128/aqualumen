package dev.aqualumen.physics;

public final class ReceiverMesherScopeTest {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static ReceiverVertex.Input[] inputs() {
        var v = new ReceiverVertex.Input(1, 2, 3, .25f, .75f, 0xff090807, .5f, 0x00900040);
        return new ReceiverVertex.Input[] {v, v, v, v};
    }
    public static void main(String[] args) throws Exception {
        var scope = new ReceiverMesherScope();
        var owner = new ReceiverMesherScope.Owner(-192, 60, 324, "Block{minecraft:sand}", "POS_Y", 0, 12, 4);
        var identity = new Object();
        var source = inputs();
        scope.begin(owner, identity, source, true);
        source[0] = null;
        var actual = scope.take(identity);
        require(actual != null && actual.owner().equals(owner)
                && actual.vertices().vertex(0).colorABGR() == 0x7f090807
                && actual.threadId() == Thread.currentThread().threadId(),
                "The matching actual encoder invocation must receive its immutable block-owned vertex snapshot");
        require(scope.take(identity) == null, "A consumed invocation cannot be promoted twice");
        System.out.println("PASS immutable block-owned synchronous encoder association and single use");
        require(actual.raw().get(0).ao() == .5f && actual.raw().get(0).light() == 0x00900040,
                "Original raw AO/light inputs must survive caller array reuse");
        scope.begin(owner, identity, inputs(), true);
        require(scope.take(new Object()) == null && scope.take(identity) == null,
                "A mismatching encoder array consumes and rejects the pending owner");
        scope.begin(owner, identity, inputs(), true);
        scope.begin(owner, identity, inputs(), false);
        require(scope.take(identity) == null, "An unsupported next quad must clear old owner provenance");
        var armed = new java.util.concurrent.CountDownLatch(1);
        var release = new java.util.concurrent.CountDownLatch(1);
        var workerResult = new java.util.concurrent.atomic.AtomicReference<ReceiverMesherScope.Capture>();
        var worker = new Thread(() -> {
            scope.begin(owner, identity, inputs(), true);
            armed.countDown();
            try { release.await(); } catch (InterruptedException error) { throw new AssertionError(error); }
            workerResult.set(scope.take(identity));
        }, "actual-worker-isolation-fixture");
        worker.start();
        require(armed.await(5, java.util.concurrent.TimeUnit.SECONDS), "Worker fixture did not arm");
        require(scope.take(identity) == null, "Another thread cannot acquire worker-owned vertices");
        release.countDown();
        worker.join(5000);
        require(!worker.isAlive() && workerResult.get() != null && workerResult.get().threadId() == worker.threadId(),
                "Wrong-thread rejection cannot erase the actual worker's pending capture");
        System.out.println("PASS raw-input ownership, mismatched/stale invocation rejection and actual two-thread isolation");
    }
}
