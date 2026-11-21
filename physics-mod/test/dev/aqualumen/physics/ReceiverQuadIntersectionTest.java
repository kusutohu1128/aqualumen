package dev.aqualumen.physics;

import java.util.List;

public final class ReceiverQuadIntersectionTest {
    private static ReceiverQuadIntersection.Quad plane(double depth, ReceiverQuadIntersection.Alpha alpha) {
        return new ReceiverQuadIntersection.Quad(
                new ReceiverQuadIntersection.Point(-1, -1, depth, 0, 0),
                new ReceiverQuadIntersection.Point(1, -1, depth, 1, 0),
                new ReceiverQuadIntersection.Point(1, 1, depth, 1, 1),
                new ReceiverQuadIntersection.Point(-1, 1, depth, 0, 1), alpha);
    }
    private static void check(boolean condition) {
        if (!condition) throw new AssertionError("Receiver primitive contract failed");
    }
    public static void main(String[] arguments) {
        var ray = new ReceiverQuadIntersection.Ray(0.2, 0, 0, 0, 0, 1, 10);
        var opaque = ReceiverQuadIntersection.Coverage.OPAQUE;
        var unknown = ReceiverQuadIntersection.Coverage.UNKNOWN;
        var transparent = ReceiverQuadIntersection.Coverage.TRANSPARENT;
        var floor = plane(4, (textureU, textureV) -> opaque);
        var leaf = plane(2, (textureU, textureV) -> textureU > 0.5 ? opaque : transparent);
        var hit = ReceiverQuadIntersection.first(ray, List.of(floor, leaf));
        check(hit.primitive() == 1 && hit.distance() == 2 && Math.abs(hit.u() - 0.6) < 1e-12);
        var holeRay = new ReceiverQuadIntersection.Ray(-0.2, 0, 0, 0, 0, 1, 10);
        check(ReceiverQuadIntersection.first(holeRay, List.of(leaf, floor)).distance() == 4);
        check(ReceiverQuadIntersection.first(ray, List.of(floor, plane(1, (textureU, textureV) -> unknown))).coverage() == unknown);
        check(ReceiverQuadIntersection.first(ray, List.of(plane(2, (textureU, textureV) -> unknown), leaf)).coverage() == unknown);
        check(ReceiverQuadIntersection.first(ray, List.of(leaf, plane(2, (textureU, textureV) -> unknown))).coverage() == unknown);
        check(ReceiverQuadIntersection.first(new ReceiverQuadIntersection.Ray(0.2, 0, 5, 0, 0, -1, 10), List.of(leaf)).distance() == 3);
        check(ReceiverQuadIntersection.first(new ReceiverQuadIntersection.Ray(2, 0, 0, 0, 0, 1, 10), List.of(leaf)) == null);
        check(ReceiverQuadIntersection.first(new ReceiverQuadIntersection.Ray(0, 0, 0, 1, 0, 0, 10), List.of(leaf)) == null);
        check(ReceiverQuadIntersection.first(new ReceiverQuadIntersection.Ray(0, 0, 0, 0, 0, 1, 1), List.of(leaf)) == null);
        check(ReceiverQuadIntersection.first(ray, List.of(plane(-1, (textureU, textureV) -> opaque))) == null);
        try {
            new ReceiverQuadIntersection.Ray(0, 0, 0, 0, 0, 2, 10);
            throw new AssertionError("Nonunit ray admitted");
        } catch (IllegalArgumentException expected) {}
        System.out.println("Receiver quad intersection: first leaf, transparent hole, unknown barrier, ties, backface and bounds verified");
    }
}
