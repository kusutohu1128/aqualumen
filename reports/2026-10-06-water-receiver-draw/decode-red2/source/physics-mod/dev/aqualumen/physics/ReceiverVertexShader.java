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
        if (input == null || uniforms == null) return null;
        int u = input.texCoord() & 65535, v = input.texCoord() >>> 16;
        float tu = (u & 32767) / 32768f + (u >>> 15 == 0 ? -1f : 1f) * uniforms.shrink[0];
        float tv = (v & 32767) / 32768f + (v >>> 15 == 0 ? -1f : 1f) * uniforms.shrink[1];
        int b = input.lightAndData() & 255, s = input.lightAndData() >>> 8 & 255;
        float[] m = uniforms.matrix;
        float block = Math.max(0f, Math.min(1f, m[0]*b + m[4]*s + m[12]));
        float sky = Math.max(0f, Math.min(1f, m[1]*b + m[5]*s + m[13]));
        int c = input.colorABGR();
        return new Output(tu, tv, block, sky, (c & 255)/255f, (c >>> 8 & 255)/255f,
                          (c >>> 16 & 255)/255f, (c >>> 24)/255f);
    }
}
