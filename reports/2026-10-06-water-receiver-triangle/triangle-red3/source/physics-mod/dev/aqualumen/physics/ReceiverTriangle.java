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
        public Sample sample(double s, double t) {
            if (!Double.isFinite(s) || !Double.isFinite(t) || s<0 || s>1 || t<0 || t>1) return null;
            int[][] triangles={{0,1,2},{2,3,0}};
            for(int index=0;index<2;index++) {
                int[] ids=triangles[index];var a=vertices[ids[0]];var b=vertices[ids[1]];var c=vertices[ids[2]];
                double det=(b.s()-a.s())*(c.t()-a.t())-(c.s()-a.s())*(b.t()-a.t());
                double[] ds={(b.t()-c.t())/det,(c.t()-a.t())/det,(a.t()-b.t())/det};
                double[] dt={(c.s()-b.s())/det,(a.s()-c.s())/det,(b.s()-a.s())/det};
                double[] weights={1+ds[0]*(s-a.s())+dt[0]*(t-a.t()),
                                  ds[1]*(s-a.s())+dt[1]*(t-a.t()),ds[2]*(s-a.s())+dt[2]*(t-a.t())};
                if(weights[0]<-1e-10 || weights[1]<-1e-10 || weights[2]<-1e-10) continue;
                return new Sample(blend(ids,weights),blend(ids,ds),blend(ids,dt),index);
            }
            return null;
        }
        private ReceiverVertexShader.Output blend(int[] ids,double[] weights) {
            double[] values=new double[8];
            for(int i=0;i<3;i++) {
                var a=vertices[ids[i]].attributes();
                float[] channels={a.u(),a.v(),a.block(),a.sky(),a.red(),a.green(),a.blue(),a.ao()};
                for(int k=0;k<8;k++) values[k]+=weights[i]*channels[k];
            }
            return new ReceiverVertexShader.Output((float)values[0],(float)values[1],(float)values[2],(float)values[3],
                    (float)values[4],(float)values[5],(float)values[6],(float)values[7]);
        }
    }
    public static Quad capture(Vertex[] vertices, int[] indices) {
        if (vertices == null || vertices.length != 4 || indices == null || indices.length != 6) return null;
        int[] pinned={0,1,2,2,3,0};
        for(int i=0;i<6;i++) if(indices[i]!=pinned[i]) return null;
        return new Quad(vertices);
    }
}
