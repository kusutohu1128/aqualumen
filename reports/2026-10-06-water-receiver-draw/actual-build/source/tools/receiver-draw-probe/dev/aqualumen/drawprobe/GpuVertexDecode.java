package dev.aqualumen.drawprobe;

import java.nio.*;
import java.util.*;
import org.lwjgl.opengl.*;
import org.lwjgl.system.MemoryUtil;

/** Owned VS-only transform feedback, using unchanged actually linked Iris VS.
 * This is a decoder fixture, not the original terrain's fragment invocation.
 */
final class GpuVertexDecode {
    private record State(int program, int vao, int array, int feedback, int feedbackBuffer, boolean discard) {
        static State read() {
            return new State(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM), GL11.glGetInteger(GL30.GL_VERTEX_ARRAY_BINDING),
                GL11.glGetInteger(GL15.GL_ARRAY_BUFFER_BINDING), GL11.glGetInteger(GL40.GL_TRANSFORM_FEEDBACK_BINDING),
                GL11.glGetInteger(GL30.GL_TRANSFORM_FEEDBACK_BUFFER_BINDING), GL11.glIsEnabled(GL30.GL_RASTERIZER_DISCARD));
        }
        void restore() {
            GL40.glBindTransformFeedback(GL40.GL_TRANSFORM_FEEDBACK, feedback);
            GL15.glBindBuffer(GL30.GL_TRANSFORM_FEEDBACK_BUFFER, feedbackBuffer);
            GL30.glBindVertexArray(vao); GL15.glBindBuffer(GL15.GL_ARRAY_BUFFER, array); GL20.glUseProgram(program);
            if (discard) GL11.glEnable(GL30.GL_RASTERIZER_DISCARD); else GL11.glDisable(GL30.GL_RASTERIZER_DISCARD);
        }
        Map<String, Object> json() {
            return Map.of("program", program, "vao", vao, "arrayBuffer", array, "transformFeedback", feedback,
                "transformFeedbackBuffer", feedbackBuffer, "rasterizerDiscard", discard);
        }
    }
    static Map<String, Object> run(String source, byte[] words, float[] lightMatrix, float[] shrink,
                                   Map<String, Integer> locations, int stride) {
        if (!GL.getCapabilities().GL_ARB_transform_feedback2 || ByteOrder.nativeOrder() != ByteOrder.LITTLE_ENDIAN
                || words.length != 56*20 || stride < 20 || stride > 128 || stride % 4 != 0)
            throw new IllegalStateException("Owned decoder fixture bounds/capabilities rejected");
        if (GL11.glGetInteger(GL40.GL_TRANSFORM_FEEDBACK_ACTIVE) != 0)
            throw new IllegalStateException("Competing transform feedback active");
        State before = State.read();
        int shader = 0, program = 0, vao = 0, input = 0, output = 0, feedback = 0;
        boolean begun = false;
        ByteBuffer vertices = MemoryUtil.memAlloc(56*stride), result = MemoryUtil.memAlloc(56*8*4);
        var metadata = new LinkedHashMap<String, Object>();
        try {
            for (int i = 0; i < 56*stride; i++) vertices.put(i, (byte)0);
            for (int i = 0; i < 56; i++) for (int j = 0; j < 20; j++) vertices.put(i*stride+j, words[i*20+j]);
            shader = GL20.glCreateShader(GL20.GL_VERTEX_SHADER); GL20.glShaderSource(shader, source); GL20.glCompileShader(shader);
            if (GL20.glGetShaderi(shader, GL20.GL_COMPILE_STATUS) == 0)
                throw new IllegalStateException("Actual-source owned VS compile failed: " + GL20.glGetShaderInfoLog(shader));
            program = GL20.glCreateProgram(); GL20.glAttachShader(program, shader);
            for (var entry : locations.entrySet()) GL20.glBindAttribLocation(program, entry.getValue(), entry.getKey());
            GL30.glTransformFeedbackVaryings(program, new String[] {"uv", "lightmap", "vertexColor"}, GL30.GL_INTERLEAVED_ATTRIBS);
            GL20.glLinkProgram(program);
            if (GL20.glGetProgrami(program, GL20.GL_LINK_STATUS) == 0)
                throw new IllegalStateException("Actual-source owned TF link failed: " + GL20.glGetProgramInfoLog(program));
            if (GL20.glGetProgrami(program, GL30.GL_TRANSFORM_FEEDBACK_VARYINGS) != 3)
                throw new IllegalStateException("Actual VS output varying set rejected");
            GL20.glUseProgram(program);
            int light = GL20.glGetUniformLocation(program, "iris_LightmapTextureMatrix"), uv = GL20.glGetUniformLocation(program, "u_TexCoordShrink");
            if (light < 0 || uv < 0) throw new IllegalStateException("Actual-source owned decoder uniforms missing");
            GL20.glUniformMatrix4fv(light, false, lightMatrix); GL20.glUniform2fv(uv, shrink);
            vao = GL30.glGenVertexArrays(); GL30.glBindVertexArray(vao);
            input = GL15.glGenBuffers(); GL15.glBindBuffer(GL15.GL_ARRAY_BUFFER, input); GL15.glBufferData(GL15.GL_ARRAY_BUFFER, vertices, GL15.GL_STATIC_DRAW);
            for (String name : locations.keySet()) GL20.glEnableVertexAttribArray(locations.get(name));
            GL30.glVertexAttribIPointer(locations.get("a_Position"), 2, GL11.GL_UNSIGNED_INT, stride, 0L);
            GL20.glVertexAttribPointer(locations.get("a_Color"), 4, GL11.GL_UNSIGNED_BYTE, true, stride, 8L);
            GL30.glVertexAttribIPointer(locations.get("a_TexCoord"), 2, GL11.GL_UNSIGNED_SHORT, stride, 12L);
            GL30.glVertexAttribIPointer(locations.get("a_LightAndData"), 4, GL11.GL_UNSIGNED_BYTE, stride, 16L);
            feedback = GL40.glGenTransformFeedbacks(); GL40.glBindTransformFeedback(GL40.GL_TRANSFORM_FEEDBACK, feedback);
            output = GL15.glGenBuffers(); GL15.glBindBuffer(GL30.GL_TRANSFORM_FEEDBACK_BUFFER, output);
            GL15.glBufferData(GL30.GL_TRANSFORM_FEEDBACK_BUFFER, result.capacity(), GL15.GL_STREAM_READ);
            GL30.glBindBufferBase(GL30.GL_TRANSFORM_FEEDBACK_BUFFER, 0, output);
            GL11.glEnable(GL30.GL_RASTERIZER_DISCARD);
            GL30.glBeginTransformFeedback(GL11.GL_POINTS); begun = true;
            GL11.glDrawArrays(GL11.GL_POINTS, 0, 56);
            GL30.glEndTransformFeedback(); begun = false;
            GL15.glGetBufferSubData(GL30.GL_TRANSFORM_FEEDBACK_BUFFER, 0, result);
            var floats = result.order(ByteOrder.nativeOrder()).asFloatBuffer();
            var actual = new ArrayList<List<Float>>();
            for (int i = 0; i < 56; i++) {
                var item = new ArrayList<Float>();
                for (int j = 0; j < 8; j++) {
                    float value = floats.get(i*8+j);
                    if (!Float.isFinite(value)) throw new IllegalStateException("Actual VS decoded nonfinite fixture output");
                    item.add(value);
                }
                actual.add(List.copyOf(item));
            }
            metadata.put("uvLightmapColor", actual); metadata.put("gpuOutputFloats", 448);
            metadata.put("unchangedActualLinkedVertexSource", true); metadata.put("outputOrder", List.of("uv.xy", "lightmap.xy", "vertexColor.rgba"));
            metadata.put("vertexInputFixtureUploaded", true); metadata.put("originalTerrainFragmentInvocation", false);
            metadata.put("before", before.json());
        } finally {
            if (begun) GL30.glEndTransformFeedback();
            before.restore();
            if (feedback != 0) GL40.glDeleteTransformFeedbacks(feedback);
            if (input != 0) GL15.glDeleteBuffers(input); if (output != 0) GL15.glDeleteBuffers(output);
            if (vao != 0) GL30.glDeleteVertexArrays(vao); if (program != 0) GL20.glDeleteProgram(program); if (shader != 0) GL20.glDeleteShader(shader);
            MemoryUtil.memFree(vertices); MemoryUtil.memFree(result);
        }
        State after = State.read();
        if (!after.equals(before)) throw new IllegalStateException("Actual listed decoder GL state not restored");
        metadata.put("after", after.json()); metadata.put("listedGLStateRestored", true);
        metadata.put("originalVertexBuffersModified", false); metadata.put("originalProgramModified", false);
        return metadata;
    }
}
