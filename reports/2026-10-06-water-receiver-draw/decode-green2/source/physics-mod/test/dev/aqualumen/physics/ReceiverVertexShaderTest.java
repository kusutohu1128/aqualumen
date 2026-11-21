package dev.aqualumen.physics;

import java.io.DataInputStream;

/** Oracle is saved actual NVIDIA transform feedback, not a second CPU formula. */
public final class ReceiverVertexShaderTest {
    private static void require(boolean yes, String message) {
        if (!yes) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        var stream = new DataInputStream(System.in);
        require(stream.readInt() == 56, "Actual 56-vertex fixture required");
        var matrix = new float[16]; var shrink = new float[2];
        for (int i = 0; i < 16; i++) matrix[i] = stream.readFloat();
        for (int i = 0; i < 2; i++) shrink[i] = stream.readFloat();
        var uniforms = ReceiverVertexShader.Uniforms.capture(matrix, shrink);
        double maximum = 0;
        for (int i = 0; i < 56; i++) {
            var input = new ReceiverVertexShader.Encoded(stream.readInt(), stream.readInt(), stream.readInt());
            var decoded = ReceiverVertexShader.decode(input, uniforms);
            require(decoded != null, "Actual encoded vertex must decode through public API");
            float[] actual = {decoded.u(), decoded.v(), decoded.block(), decoded.sky(),
                              decoded.red(), decoded.green(), decoded.blue(), decoded.ao()};
            for (int c = 0; c < 8; c++) {
                float gpu = stream.readFloat();
                double error = Math.abs((double)actual[c] - gpu);
                require(Float.isFinite(actual[c]) && error <= 1e-6,
                    "Actual NVIDIA output mismatch at vertex " + i + " channel " + c + ": " + error);
                maximum = Math.max(maximum, error);
            }
        }
        require(stream.read() == -1, "Fixture extent exact");
        System.out.println("PASS all 448 actual GPU UV/lightmap/color floats; maximum error=" + maximum);
        var corrupted = matrix.clone(); corrupted[0] = Float.NaN;
        require(ReceiverVertexShader.Uniforms.capture(corrupted, shrink) == null,
                "Nonfinite actual matrix must remain unready, not guessed illumination");
        System.out.println("PASS nonfinite matrix rejected");
    }
}
