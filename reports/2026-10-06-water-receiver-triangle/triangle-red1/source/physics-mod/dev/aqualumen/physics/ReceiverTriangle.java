package dev.aqualumen.physics;

/** Owned full-unit face interpolation in encoded vertex order. Not source readiness. */
public final class ReceiverTriangle {
    private ReceiverTriangle() {}
    public record Vertex(double s, double t, ReceiverVertexShader.Output attributes) {}
    public record Sample(ReceiverVertexShader.Output value, ReceiverVertexShader.Output alongS,
                         ReceiverVertexShader.Output alongT, int triangle) {}
    public static final class Quad {
        private final Vertex[] vertices;
        private Quad(Vertex[] vertices) { this.vertices = vertices.clone(); }
        public Sample sample(double s, double t) { return null; }
    }
    public static Quad capture(Vertex[] vertices, int[] indices) {
        if (vertices == null || vertices.length != 4 || indices == null || indices.length != 6) return null;
        return new Quad(vertices);
    }
}
