package dev.aqualumen.physics;
import java.io.DataInputStream;

/** Actual archived vertex outputs with separately calculated face-point oracle. */
public final class ReceiverTriangleTest {
    private static void require(boolean yes,String message) { if(!yes) throw new AssertionError(message); }
    public static void main(String[] args) throws Exception {
        var in = new DataInputStream(System.in);
        require(in.readInt()==14,"Exact actual face count");
        var faces = new ReceiverTriangle.Quad[14];
        for(int f=0;f<14;f++) {
            var vertices = new ReceiverTriangle.Vertex[4];
            for(int v=0;v<4;v++) {
                double s=in.readDouble(),t=in.readDouble();
                var a=new ReceiverVertexShader.Output(in.readFloat(),in.readFloat(),in.readFloat(),in.readFloat(),
                                                      in.readFloat(),in.readFloat(),in.readFloat(),in.readFloat());
                vertices[v]=new ReceiverTriangle.Vertex(s,t,a);
            }
            int[] indices = new int[6]; for(int i=0;i<6;i++) indices[i]=in.readInt();
            faces[f]=ReceiverTriangle.capture(vertices,indices);
            require(faces[f]!=null,"Actual full-unit face must be captured");
        }
        int count=in.readInt(); double maximum=0;
        for(int i=0;i<count;i++) {
            int f=in.readInt(); double s=in.readDouble(),t=in.readDouble();
            var hit=faces[f].sample(s,t);
            require(hit!=null,"Actual face point must interpolate in pinned triangle order");
            var a=hit.value(); float[] values={a.u(),a.v(),a.block(),a.sky(),a.red(),a.green(),a.blue(),a.ao()};
            for(int c=0;c<8;c++) {
                double expected=in.readDouble(); double error=Math.abs(values[c]-expected);
                require(Float.isFinite(values[c]) && error<=1e-6,"Actual face-point interpolation mismatch");
                maximum=Math.max(maximum,error);
            }
        }
        require(in.read()==-1,"Exact external fixture extent");
        System.out.println("PASS "+count+" actual-face and supplemental point samples; max scalar error="+maximum);
        var attr=new ReceiverVertexShader.Output(.4f,.7f,.0625f,.5625f,1,1,1,.5f);
        var v=new ReceiverTriangle.Vertex[]{new ReceiverTriangle.Vertex(0,0,attr),new ReceiverTriangle.Vertex(1,0,attr),
                                           new ReceiverTriangle.Vertex(1,1,attr),new ReceiverTriangle.Vertex(0,1,attr)};
        require(ReceiverTriangle.capture(v,new int[]{1,2,3,3,0,1})==null,
                "Unqualified opposite diagonal must remain unsupported, not be silently substituted");
        System.out.println("PASS unqualified triangle diagonal rejected");
        var duplicate=v.clone();duplicate[3]=duplicate[0];
        require(ReceiverTriangle.capture(duplicate,new int[]{0,1,2,2,3,0})==null,
                "Incomplete or degenerate face must remain unsupported");
        System.out.println("PASS degenerate face rejected");
        int[] pinned={0,1,2,2,3,0};
        var owned=ReceiverTriangle.capture(v,pinned);var before=owned.sample(.25,.75);
        v[0]=null;pinned[0]=3;
        require(owned.sample(.25,.75).equals(before),"Mutable caller arrays cannot alter retained face");
        require(owned.sample(Double.NaN,.5)==null && owned.sample(-.01,.5)==null && owned.sample(.5,1.01)==null,
                "Outside or nonfinite points cannot become a source");
        var broken=new ReceiverTriangle.Vertex[]{new ReceiverTriangle.Vertex(0,0,attr),null,
                new ReceiverTriangle.Vertex(1,1,attr),new ReceiverTriangle.Vertex(0,1,attr)};
        require(ReceiverTriangle.capture(broken,new int[]{0,1,2,2,3,0})==null,"Missing vertex rejected");
        for(double s:new double[]{.1,.4,.8}) {
            var q=owned.sample(s,.3);double epsilon=1e-4;
            var shifted=owned.sample(s+epsilon,.3);
            require(Math.abs(shifted.value().u()-q.value().u()-epsilon*q.alongS().u())<1e-6,
                    "UV gradient agrees with face-local interpolation");
        }
        System.out.println("PASS retained face ownership, point/input rejection and local UV gradient");
    }
}
