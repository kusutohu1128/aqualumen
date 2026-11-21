package dev.aqualumen.physics;

/** Owns pre-encoder Sodium quad inputs; not a shaded source or live producer.
 * xyz/UV stay unquantized. Only separate-AO color and packed light codes are
 * prepared for the pinned Iris encoder convention, not a lightmap matrix.
 */
public final class ReceiverVertex {
    private ReceiverVertex() {}
    public record Input(float x, float y, float z, float u, float v,
                        int colorABGR, float ao, int light) {}
    public record Encoded(float x, float y, float z, float u, float v,
                          int colorABGR, int blockByte, int skyByte) {}
    public static final class Quad {
        private final Encoded[] values;
        private Quad(Encoded[] values) { this.values = values.clone(); }
        public Encoded vertex(int index) { return values[index]; }
        public int size() { return values.length; }
    }
    /** Null is unready/unsupported; ordinary source readiness is not implied. */
    public static Quad capture(Input[] vertices, boolean separateAo) {
        return null;
    }
}
