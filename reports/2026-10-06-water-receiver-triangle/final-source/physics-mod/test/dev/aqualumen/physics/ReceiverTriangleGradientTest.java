package dev.aqualumen.physics;

/** Supplemental affine material-UV control; not actual screen derivatives/LOD. */
public final class ReceiverTriangleGradientTest {
    private static void close(float value,double expected) {
        if(!Float.isFinite(value) || Math.abs(value-expected)>1e-6) throw new AssertionError("Affine UV gradient mismatch");
    }
    public static void main(String[] args) {
        double[][] corners={{0,0},{1,0},{1,1},{0,1}};
        var vertices=new ReceiverTriangle.Vertex[4];
        for(int i=0;i<4;i++) {
            double s=corners[i][0],t=corners[i][1];
            var a=new ReceiverVertexShader.Output((float)(.1+.5*s+.1*t),(float)(.2-.05*s+.2*t),.0625f,.5f,1,1,1,.7f);
            vertices[i]=new ReceiverTriangle.Vertex(s,t,a);
        }
        var face=ReceiverTriangle.capture(vertices,new int[]{0,1,2,2,3,0});
        for(double[] p:new double[][]{{.2,.7},{.8,.3}}) {
            var value=face.sample(p[0],p[1]);
            close(value.alongS().u(),.5);close(value.alongT().u(),.1);
            close(value.alongS().v(),-.05);close(value.alongT().v(),.2);
            close(value.value().u(),.1+.5*p[0]+.1*p[1]);
            close(value.value().v(),.2-.05*p[0]+.2*p[1]);
        }
        System.out.println("PASS varying affine UV value and signed local gradients in both triangles; not screen LOD");
    }
}
