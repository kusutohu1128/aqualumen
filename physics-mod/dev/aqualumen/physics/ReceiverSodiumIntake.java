package dev.aqualumen.physics;

import net.caffeinemc.mods.sodium.client.render.chunk.vertex.format.ChunkVertexEncoder.Vertex;
import net.irisshaders.iris.shaderpack.materialmap.WorldRenderingSettings;

public final class ReceiverSodiumIntake {
    private static final ReceiverMemberCache members=new ReceiverMemberCache();
    private ReceiverSodiumIntake() { }
    static String canonicalFace(String face) { return "POS_Y".equals(face) ? "UP" : face; }
    public static void beforePush(Object renderer, Object quad) {
        var scope = ReceiverSodiumScope.forRenderer(renderer);
        if (scope == null) return;
        try {
            Object position = field(renderer,"pos"), offset = field(renderer,"posOffset"), slice = field(renderer,"slice");
            String face = canonicalFace(((Enum<?>)quad.getClass().getMethod("normalFace").invoke(quad)).name());
            Vertex[] vertices = (Vertex[])field(renderer,"vertices");
            var inputs = new ReceiverVertex.Input[vertices.length];
            for (int index = 0; index < vertices.length; index++) {
                var vertex = vertices[index];
                inputs[index] = new ReceiverVertex.Input(vertex.x,vertex.y,vertex.z,vertex.u,vertex.v,vertex.color,vertex.ao,vertex.light);
            }
            scope.accept(field(slice,"level"), coordinate(position,"method_10263"), coordinate(position,"method_10264"),
                    coordinate(position,"method_10260"), field(renderer,"state").toString(), face,
                    offset.getClass().getField("x").getFloat(offset), offset.getClass().getField("y").getFloat(offset),
                    offset.getClass().getField("z").getFloat(offset), inputs, WorldRenderingSettings.INSTANCE.shouldUseSeparateAo());
        } catch (ReflectiveOperationException | ClassCastException error) { scope.reject(error.toString()); }
    }
    static Object field(Object object, String name) throws ReflectiveOperationException {
        try { return members.field(object.getClass(),name).get(object); }
        catch(IllegalStateException error) { throw new ReflectiveOperationException("Receiver field metadata unavailable",error); }
    }
    private static int coordinate(Object position, String method) throws ReflectiveOperationException {
        return (int)position.getClass().getMethod(method).invoke(position);
    }
}
