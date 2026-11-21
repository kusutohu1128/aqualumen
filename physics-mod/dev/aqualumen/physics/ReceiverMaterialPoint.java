package dev.aqualumen.physics;

public record ReceiverMaterialPoint(ReceiverRadianceVolume.Epoch epoch,double x,double y,double z,
        float normalX,float normalY,float normalZ,ReceiverVertexShader.Output attributes) {
    public ReceiverMaterialPoint {
        java.util.Objects.requireNonNull(epoch);java.util.Objects.requireNonNull(attributes);
        if(!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)
                || !Float.isFinite(normalX) || !Float.isFinite(normalY) || !Float.isFinite(normalZ)
                || Math.abs((double)normalX*normalX+(double)normalY*normalY+(double)normalZ*normalZ-1)>0.0001)
            throw new IllegalArgumentException("Invalid material source position/normal");
        for(float value:new float[]{attributes.u(),attributes.v(),attributes.block(),attributes.sky(),
                attributes.red(),attributes.green(),attributes.blue(),attributes.ao()})
            if(!Float.isFinite(value) || value<0 || value>1)
                throw new IllegalArgumentException("Unqualified material source attributes");
    }
}
