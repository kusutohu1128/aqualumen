package dev.aqualumen.physics;

import net.caffeinemc.mods.sodium.api.util.ColorABGR;

public final class ReceiverVertexTest {
    private static void require(boolean yes, String message) {
        if (!yes) throw new AssertionError(message);
    }
    private static ReceiverVertex.Input input(float ao, int light) {
        return new ReceiverVertex.Input(1, 2, 3, .25f, .75f, 0xff090807, ao, light);
    }
    private static ReceiverVertex.Input[] quad(float ao, int light) {
        var v = input(ao, light);
        return new ReceiverVertex.Input[] {v, v, v, v};
    }
    public static void main(String[] args) {
        var captured = ReceiverVertex.capture(quad(.5f, 0x00900040), true);
        require(captured != null && captured.size() == 4, "Separate-AO actual input quad must be captured");
        var v = captured.vertex(0);
        int actualPinnedEncoderColor = ColorABGR.withAlpha(0xff090807, .5f);
        require(actualPinnedEncoderColor == 0x7f090807, "Pinned Sodium AO channel calibration");
        require(v.colorABGR() == actualPinnedEncoderColor && v.blockByte() == 64 && v.skyByte() == 144,
                "RGB must remain untinted twice; actual AO/light precision must be retained");
        require(v.x() == 1 && v.y() == 2 && v.z() == 3 && v.u() == .25f && v.v() == .75f,
                "Pre-encoder geometry/UV retained, not declared GPU-quantized");
        System.out.println("PASS separate-AO actual pinned Sodium color reference and smoothed light codes");
        require(ReceiverVertex.capture(quad(Float.NaN, 0x00900040), true) == null,
                "Nonfinite AO must remain unready, not become a guessed zero-light vertex");
        System.out.println("PASS nonfinite AO rejected");
    }
}
