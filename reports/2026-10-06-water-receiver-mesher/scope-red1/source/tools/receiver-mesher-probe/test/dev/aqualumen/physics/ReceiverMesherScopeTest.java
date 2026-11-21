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
    }
}
