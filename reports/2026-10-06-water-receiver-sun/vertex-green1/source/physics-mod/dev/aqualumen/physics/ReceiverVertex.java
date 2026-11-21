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
        if (!separateAo || vertices == null || vertices.length != 4) return null;
        Encoded[] result = new Encoded[4];
        for (int i = 0; i < 4; i++) {
            Input v = vertices[i];
            int alpha = (int)(v.ao() * 255f) & 255;
            int color = (v.colorABGR() & 0x00ffffff) | (alpha << 24);
            int block = Math.max(8, Math.min(248, v.light() & 255));
            int sky = Math.max(8, Math.min(248, (v.light() >>> 16) & 255));
            result[i] = new Encoded(v.x(), v.y(), v.z(), v.u(), v.v(), color, block, sky);
        }
        return new Quad(result);
    }
}
