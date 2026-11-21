package dev.aqualumen.physics;

/** Immutable vanilla face inputs, not shaded radiance or GPU/texture readiness. */
public final class ReceiverFace {
    private ReceiverFace() {}
    public record UV(double u, double v) {}
    public record Sprite(String atlas, String id, float minU, float maxU, float minV, float maxV) {}
    public record Color(float r, float g, float b) {}
    public record Face(int axis, int sign, Sprite sprite, UV origin, UV alongS, UV alongT,
                       Color vertexColor, Color tint, boolean shade, int skyLight, int blockLight,
                       float vanillaBrightness) {
        /** Local coordinates along the two world axes other than the normal axis. */
        public UV uvAt(double s, double t) {
            if (!Double.isFinite(s) || !Double.isFinite(t) || s < 0 || s > 1 || t < 0 || t > 1)
                throw new IllegalArgumentException("Face coordinates must be finite and bounded");
            return new UV(origin.u()+s*alongS.u()+t*alongT.u(), origin.v()+s*alongS.v()+t*alongT.v());
        }
    }
    /** Null means unsupported. Packed vertex layout is pinned vanilla 4*8 ints. */
    public static Face decode(int[] data, int normalX, int normalY, int normalZ, Sprite sprite,
                              int tintRGB, boolean shade, int skyLight, int blockLight, float brightness) {
        if (data==null || data.length!=32 || sprite==null || sprite.atlas()==null || sprite.atlas().isEmpty()
                || sprite.id()==null || sprite.id().isEmpty() || skyLight<0 || skyLight>15 || blockLight<0 || blockLight>15
                || !Float.isFinite(brightness) || brightness<0 || brightness>1) return null;
        int[] normal={normalX,normalY,normalZ};int axis=-1;
        for(int i=0;i<3;i++) if(normal[i]!=0) {
            if(axis!=-1 || Math.abs(normal[i])!=1) return null;axis=i;
        }
        if(axis<0) return null;
        float[] bounds={sprite.minU(),sprite.maxU(),sprite.minV(),sprite.maxV()};
        for(float value:bounds) if(!Float.isFinite(value) || value<0 || value>1) return null;
        if(bounds[0]>=bounds[1] || bounds[2]>=bounds[3]) return null;
        int sAxis=(axis+1)%3,tAxis=(axis+2)%3;
        UV[] corners=new UV[4];int[] order=new int[4];
        for(int v=0;v<4;v++) {
            double[] xyz={Float.intBitsToFloat(data[v*8]),Float.intBitsToFloat(data[v*8+1]),Float.intBitsToFloat(data[v*8+2])};
            for(double value:xyz) if(!Double.isFinite(value)) return null;
            if(Math.abs(xyz[axis]-(normal[axis]>0?1:0))>1e-6) return null;
            int s=corner(xyz[sAxis]),t=corner(xyz[tAxis]);if(s<0 || t<0) return null;
            int index=s+2*t;if(corners[index]!=null) return null;order[v]=index;
            float u=Float.intBitsToFloat(data[v*8+4]),w=Float.intBitsToFloat(data[v*8+5]);
            if(!Float.isFinite(u) || !Float.isFinite(w) || u<bounds[0]-1e-7 || u>bounds[1]+1e-7
                    || w<bounds[2]-1e-7 || w>bounds[3]+1e-7 || data[v*8+3]!=data[3]) return null;
            corners[index]=new UV(u,w);
        }
        if((data[3]>>>24)!=255) return null;
        int area=0;
        for(int v=0;v<4;v++) {
            int difference=order[v]^order[(v+1)%4];if(difference!=1 && difference!=2) return null;
            area+=(order[v]&1)*(order[(v+1)%4]>>1)-(order[(v+1)%4]&1)*(order[v]>>1);
        }
        if(area!=2*normal[axis]) return null;
        UV o=corners[0],s=new UV(corners[1].u()-o.u(),corners[1].v()-o.v()),t=new UV(corners[2].u()-o.u(),corners[2].v()-o.v());
        if(Math.abs(o.u()+s.u()+t.u()-corners[3].u())>1e-7 || Math.abs(o.v()+s.v()+t.v()-corners[3].v())>1e-7
                || Math.abs(s.u()*t.v()-s.v()*t.u())<1e-12) return null;
        int color=data[3];
        return new Face(axis,normal[axis],sprite,o,s,t,
                new Color((color&255)/255f,((color>>>8)&255)/255f,((color>>>16)&255)/255f),
                new Color(((tintRGB>>>16)&255)/255f,((tintRGB>>>8)&255)/255f,(tintRGB&255)/255f),
                shade,skyLight,blockLight,brightness);
    }
    private static int corner(double value) {return Math.abs(value)<1e-6?0:Math.abs(value-1)<1e-6?1:-1;}
}
