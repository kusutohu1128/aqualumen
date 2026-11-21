package dev.aqualumen.bench;

/** Fixed looking-up views use eye depth, never an arbitrary camera offset. */
public final class UnderwaterSceneTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        var near = UnderwaterScene.parse("underwater-up-near");
        check(near != null && near.x() == 448.5 && near.z() == -383.5 && near.pitch() == -90,
            "Near upward view must use the approved fixed ocean position and look straight up");
        check(Math.abs(near.playerY() + 1.62 - (62.8889 - .5)) < 1e-10,
            "Near camera eye must start half a metre below the established fluid surface");
        var deep = UnderwaterScene.parse("underwater-up-deep");
        var tilt = UnderwaterScene.parse("underwater-up-tilt");
        check(deep != null && deep.eyeDepth() == 3.25 && deep.pitch() == -90 &&
              Math.abs(deep.playerY() + 1.62 - (62.8889 - 3.25)) < 1e-10,
            "Deep straight-up control must put the actual eye3.25m below the same surface");
        check(tilt != null && tilt.pitch() == -65 && tilt.eyeDepth() == .5 && tilt.playerY() == near.playerY(),
            "Tilt control changes only the viewing angle at the near eye depth");
        check(UnderwaterScene.parse("underwater") == null && UnderwaterScene.parse("underwater-up-side") == null,
            "Existing underwater and unknown views must not be silently remapped");
        check(UnderwaterScene.authorized("AqualumenNaturalV2", "b22dbccb-2970-41e6-847f-f183b1ec923d", 308060),
            "Established ocean poses require the exact approved world and seed");
        check(!UnderwaterScene.authorized("AqualumenNaturalV1", "b22dbccb-2970-41e6-847f-f183b1ec923d", 308060) &&
              !UnderwaterScene.authorized("AqualumenNaturalV2", "00000000-0000-0000-0000-000000000000", 308060) &&
              !UnderwaterScene.authorized("AqualumenNaturalV2", "b22dbccb-2970-41e6-847f-f183b1ec923d", 308061),
            "No other world UUID or seed may reuse the fixed ocean poses");
        double[] player = {near.x(), near.playerY(), near.z()};
        double[] eye = {near.x(), 62.8889-.5, near.z()};
        check(UnderwaterScene.matches(near, true, true, "WATER", player, eye, eye),
            "Measured first-person water eye at the requested depth may be captured");
        check(!UnderwaterScene.matches(near, false, true, "WATER", player, eye, eye) &&
              !UnderwaterScene.matches(near, true, false, "WATER", player, eye, eye) &&
              !UnderwaterScene.matches(near, true, true, "NONE", player, eye, eye) &&
              !UnderwaterScene.matches(near, true, true, "WATER", player, eye, new double[]{eye[0], eye[1]+1, eye[2]}) &&
              !UnderwaterScene.matches(near, true, true, "WATER", player, new double[]{eye[0], 62.9, eye[2]}, eye) &&
              !UnderwaterScene.matches(near, true, true, "WATER", new double[]{Double.NaN, player[1], player[2]}, eye, eye),
            "Wrong perspective, fluid state, camera identity/depth and nonfinite positions must reject capture");
        System.out.println("Underwater fixed near/deep/tilt pose regressions passed");
    }
}
