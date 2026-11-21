package dev.aqualumen.physics;

public final class ReceiverMaterialTriangle {
    public record Vertex(double x,double y,double z,ReceiverVertexShader.Output attributes) {
        public Vertex {
            java.util.Objects.requireNonNull(attributes);
            if(!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z))
                throw new IllegalArgumentException("Nonfinite material vertex");
        }
    }
    private final ReceiverRadianceVolume.Epoch epoch;
    private final Vertex first,second,third;
    private final float normalX,normalY,normalZ;
    public ReceiverMaterialTriangle(ReceiverRadianceVolume.Epoch epoch,Vertex first,Vertex second,Vertex third) {
        this.epoch=java.util.Objects.requireNonNull(epoch);
        this.first=java.util.Objects.requireNonNull(first);
        this.second=java.util.Objects.requireNonNull(second);
        this.third=java.util.Objects.requireNonNull(third);
        double edgeX=second.x()-first.x(),edgeY=second.y()-first.y(),edgeZ=second.z()-first.z();
        double otherX=third.x()-first.x(),otherY=third.y()-first.y(),otherZ=third.z()-first.z();
        double nx=edgeY*otherZ-edgeZ*otherY,ny=edgeZ*otherX-edgeX*otherZ,nz=edgeX*otherY-edgeY*otherX;
        double squared=nx*nx+ny*ny+nz*nz;
        if(!Double.isFinite(squared) || squared<1e-16)
            throw new IllegalArgumentException("Degenerate material triangle");
        double length=Math.sqrt(squared);
        normalX=(float)(nx/length);normalY=(float)(ny/length);normalZ=(float)(nz/length);
        for(Vertex vertex:new Vertex[]{first,second,third})
            new ReceiverMaterialPoint(epoch,vertex.x(),vertex.y(),vertex.z(),normalX,normalY,normalZ,vertex.attributes());
    }
    public ReceiverMaterialPoint sample(double firstWeight,double secondWeight,double thirdWeight,boolean reverseNormal) {
        double[] weights={firstWeight,secondWeight,thirdWeight};
        for(double weight:weights)if(!Double.isFinite(weight) || weight<0 || weight>1)
            throw new IllegalArgumentException("Invalid material barycentric weights");
        if(Math.abs(firstWeight+secondWeight+thirdWeight-1)>1e-8)
            throw new IllegalArgumentException("Material barycentric weights do not sum to one");
        Vertex[] vertices={first,second,third};double x=0,y=0,z=0;double[] channels=new double[8];
        for(int index=0;index<3;index++) {
            Vertex vertex=vertices[index];double weight=weights[index];var value=vertex.attributes();
            x+=weight*vertex.x();y+=weight*vertex.y();z+=weight*vertex.z();
            float[] attributes={value.u(),value.v(),value.block(),value.sky(),value.red(),value.green(),value.blue(),value.ao()};
            for(int channel=0;channel<8;channel++)channels[channel]+=weight*attributes[channel];
        }
        var value=new ReceiverVertexShader.Output((float)channels[0],(float)channels[1],(float)channels[2],
                (float)channels[3],(float)channels[4],(float)channels[5],(float)channels[6],(float)channels[7]);
        float sign=reverseNormal?-1:1;
        return new ReceiverMaterialPoint(epoch,x,y,z,sign*normalX,sign*normalY,sign*normalZ,value);
    }
}
