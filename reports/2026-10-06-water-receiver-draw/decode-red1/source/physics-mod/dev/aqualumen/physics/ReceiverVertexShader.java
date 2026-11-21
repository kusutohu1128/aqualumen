package dev.aqualumen.physics;

/** Pinned Iris/Sodium UV, lightmap and color decoding, not shaded radiance. */
public final class ReceiverVertexShader {
    private ReceiverVertexShader() {}
    public record Encoded(int colorABGR, int texCoord, int lightAndData) {}
    public record Output(float u, float v, float block, float sky,
                         float red, float green, float blue, float ao) {}
    public static final class Uniforms {
        private final float[] matrix, shrink;
        private Uniforms(float[] matrix, float[] shrink) {
            this.matrix = matrix.clone(); this.shrink = shrink.clone();
        }
        public static Uniforms capture(float[] matrix, float[] shrink) {
            if (matrix == null || matrix.length != 16 || shrink == null || shrink.length != 2) return null;
            return new Uniforms(matrix, shrink);
        }
    }
    public static Output decode(Encoded input, Uniforms uniforms) {
        return null;
    }
}
