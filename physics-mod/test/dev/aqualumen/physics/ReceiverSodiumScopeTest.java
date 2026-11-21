package dev.aqualumen.physics;

public final class ReceiverSodiumScopeTest {
    private static void encodeGeometry(ReceiverSodiumScope scope, ReceiverVertex.Input[] vertices) {
        var prepared = ReceiverVertex.capture(vertices,true);
        var packed = new java.util.ArrayList<ReceiverVertexShader.Encoded>();
        for (int index = 0; index < 4; index++) {
            var vertex = prepared.vertex(index);
            packed.add(new ReceiverVertexShader.Encoded(vertex.colorABGR(),0x12345678,
                    vertex.blockByte() | vertex.skyByte() << 8));
        }
        scope.encoded(52,packed);
        packed.clear();
    }
    private static ReceiverVertex.Input[] inputs() {
        return new ReceiverVertex.Input[]{
            new ReceiverVertex.Input(3,5,6,.1f,.2f,0xff123456,.8f,0x00f00080),
            new ReceiverVertex.Input(4,5,6,.3f,.2f,0xff234567,.7f,0x00e00070),
            new ReceiverVertex.Input(4,5,7,.3f,.4f,0xff345678,.6f,0x00d00060),
            new ReceiverVertex.Input(3,5,7,.1f,.4f,0xff456789,.5f,0x00c00050)};
    }
    public static void main(String[] args) throws Exception {
        Object world = new Object(), renderer = new Object();
        var epoch = new ReceiverRadianceVolume.Epoch(world,2,1);
        check(ReceiverSodiumIntake.canonicalFace("POS_Y").equals("UP") &&
                !ReceiverSodiumIntake.canonicalFace("NEG_Y").equals("UP"),"Pinned Sodium positive-Y face mapping");
        try (var scope = ReceiverSodiumScope.open(epoch,renderer,35,52,70,"sand")) {
            check(ReceiverSodiumScope.forRenderer(new Object()) == null,"Foreign renderer cannot provide owned inputs");
            var vertices = inputs();
            scope.accept(world,35,52,70,"sand","UP",3,4,6,vertices,true);
            vertices[0] = null;
            var result = scope.finish();
            check(result != null && result.raw().get(0).ao() == .8f && result.encoded().vertex(0).skyByte() == 240,
                    "Owned raw AO/light and prepared separate-AO codes");
            check(result.encoded().vertex(0).colorABGR() == 0xcc123456,"Actual AO preserved rather than fabricated");
            boolean nestedRejected = false;
            try { ReceiverSodiumScope.open(epoch,renderer,35,52,70,"sand"); } catch (IllegalStateException expected) { nestedRejected = true; }
            check(nestedRejected,"Nested scope rejection");
            var isolated = new java.util.concurrent.atomic.AtomicBoolean();
            var other = new Thread(() -> isolated.set(ReceiverSodiumScope.forRenderer(renderer) == null));
            other.start(); other.join();
            check(isolated.get(),"Other thread cannot read pending owner");
        }
        check(ReceiverSodiumScope.forRenderer(renderer) == null,"Closed owner cannot persist");
        try (var scope = ReceiverSodiumScope.openGeometry(epoch,renderer,35,52,70,"kelp")) {
            var vertices = inputs();
            scope.accept(world,35,52,70,"kelp","UNASSIGNED",3,4,6,vertices,true);
            check(scope.finishGeometry() == null && scope.wantsEncoding(),"Unencoded model cannot finish");
            encodeGeometry(scope,vertices);
            vertices[0] = null;
            scope.accept(world,35,52,70,"kelp","NEG_X",3,4,6,inputs(),true);
            encodeGeometry(scope,inputs());
            var result = scope.finishGeometry();
            check(result != null && result.faces().size() == 2 && result.faces().get(0).raw().get(0) != null,
                    "All model faces copied without UP filtering or array aliasing");
            check(result.faces().get(0).offsetX() == 3 && result.epoch() == epoch,
                    "Actual model offset and epoch retained");
            check(result.faces().get(0).packed().size() == 4 && result.faces().get(1).stride() == 52,
                    "Every model face has defensive owned packed encoder inputs");
            check(scope.finish() == null && !scope.wantsEncoding(),"Geometry cannot become a cube radiance source");
        }
        for (int negative = 0; negative < 3; negative++) {
            try (var scope = ReceiverSodiumScope.openGeometry(epoch,renderer,35,52,70,"kelp")) {
                scope.accept(world,35,52,70,"kelp","UNASSIGNED",3,4,6,inputs(),true);
                if (negative == 0) scope.accept(world,35,52,70,"kelp","NEG_X",3,4,6,inputs(),true);
                else if (negative == 1) scope.encoded(52,java.util.List.of());
                else {
                    encodeGeometry(scope,inputs());
                    encodeGeometry(scope,inputs());
                }
                check(scope.finishGeometry() == null,"Missing, skipped or duplicate model encoding rejected");
            }
        }
        for (int negative = 0; negative < 6; negative++) {
            try (var scope = ReceiverSodiumScope.openGeometry(epoch,renderer,35,52,70,"kelp")) {
                check(scope.finishGeometry() == null,"Empty model is not complete geometry");
                scope.accept(world,35,52,70,"kelp","UNASSIGNED",3,4,6,inputs(),true);
                encodeGeometry(scope,inputs());
                var vertices = inputs();
                if (negative == 2) vertices[0] = null;
                scope.accept(negative == 0 ? new Object() : world,35,52,70,negative == 1 ? "sand" : "kelp",
                        "UNASSIGNED",negative == 3 ? Float.NaN : 3,4,6,vertices,negative != 4);
                if (negative == 5) {
                    encodeGeometry(scope,inputs());
                    for (int index = 0; index < 254; index++) {
                        scope.accept(world,35,52,70,"kelp","UNASSIGNED",3,4,6,inputs(),true);
                        encodeGeometry(scope,inputs());
                    }
                    scope.accept(world,35,52,70,"kelp","UNASSIGNED",3,4,6,inputs(),true);
                }
                check(scope.finishGeometry() == null,"Partial, foreign or oversized geometry remains unavailable");
            }
        }
        for (int negative = -1; negative < 4; negative++) {
            try (var scope = ReceiverSodiumScope.open(epoch,renderer,35,52,70,"sand")) {
                scope.accept(world,35,52,70,"sand","UP",3,4,6,inputs(),true);
                var packed = new java.util.ArrayList<ReceiverVertexShader.Encoded>();
                for (int index = 0; index < 4; index++) {
                    var prepared = scope.finish().encoded().vertex(index);
                    packed.add(new ReceiverVertexShader.Encoded(prepared.colorABGR(),0x12345678,
                            prepared.blockByte() | prepared.skyByte() << 8));
                }
                if (negative == 0) packed.remove(3);
                if (negative == 1) packed.set(0,new ReceiverVertexShader.Encoded(0,0,0));
                scope.encoded(negative == 2 ? 19 : 52,packed);
                if (negative == 3) scope.encoded(52,packed);
                var result = scope.finish();
                if (negative >= 0) check(result == null,"Incomplete/mismatched/duplicate encoder capture rejection");
                else {
                    packed.clear();
                    check(result.packed().size() == 4 && result.stride() == 52 && !scope.wantsEncoding(),
                            "Actual packed UV/color/light copies outlive native buffer and original list");
                }
            }
        }
        for (int negative = 0; negative < 5; negative++) {
            try (var scope = ReceiverSodiumScope.open(epoch,renderer,35,52,70,"sand")) {
                var vertices = inputs();
                if (negative == 1) vertices[0] = new ReceiverVertex.Input(3.2f,5,6,.1f,.2f,0xff123456,.8f,0x00f00080);
                scope.accept(negative == 0 ? new Object() : world,35,52,70,negative == 2 ? "stone" : "sand","UP",3,4,6,vertices,negative != 3);
                if (negative == 4) scope.accept(world,35,52,70,"sand","UP",3,4,6,vertices,true);
                check(scope.finish() == null,"Foreign world, incomplete face, changed state, nonseparate AO or multiple top faces cannot become source");
            }
        }
        System.out.println("PASS owned synchronous Sodium scope: raw AO/light/color copies, full-face/identity/separate-AO qualification and thread/nesting/expiry negatives; CPU fixtures, not live material or radiance");
    }
    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
