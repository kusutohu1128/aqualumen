package dev.aqualumen.physics;

/** CPU-only immutable static opaque mip0 texels; not filtered or shaded radiance. */
public final class ReceiverTexture {
    private ReceiverTexture() {}
    public record Sample(int x,int y,int red,int green,int blue,int alpha) {}
    public static final class Snapshot {
        private final ReceiverFace.Sprite sprite;
        private final int width,height;
        private final int[] pixels;
        private Snapshot(ReceiverFace.Sprite sprite,int width,int height,int[] pixels) {
            this.sprite=sprite;this.width=width;this.height=height;this.pixels=pixels;
        }
        public int width(){return width;}
        public int height(){return height;}
        public String rgbaSHA256(){
            byte[] bytes=new byte[pixels.length*4];
            for(int i=0;i<pixels.length;i++)for(int c=0;c<4;c++)bytes[i*4+c]=(byte)(pixels[i]>>>(8*c));
            try{return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes));}
            catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException(e);}
        }
        public Sample sample(ReceiverFace.Face face,double s,double t) {
            if(face==null || !face.sprite().equals(sprite))return null;
            var uv=face.uvAt(s,t);
            if(!Double.isFinite(uv.u()) || !Double.isFinite(uv.v()) || uv.u()<sprite.minU()-1e-7 || uv.u()>sprite.maxU()+1e-7
                    || uv.v()<sprite.minV()-1e-7 || uv.v()>sprite.maxV()+1e-7)return null;
            int x=Math.max(0,Math.min(width-1,(int)Math.floor((uv.u()-sprite.minU())/(sprite.maxU()-sprite.minU())*width)));
            int y=Math.max(0,Math.min(height-1,(int)Math.floor((uv.v()-sprite.minV())/(sprite.maxV()-sprite.minV())*height)));
            int value=pixels[y*width+x];
            return new Sample(x,y,value&255,(value>>>8)&255,(value>>>16)&255,(value>>>24)&255);
        }
    }
    /** Inputs are the pinned NativeImage ABGR integers in top-row-first order. */
    public static Snapshot capture(ReceiverFace.Sprite sprite,int width,int height,int[] abgr,boolean animated) {
        if(animated || sprite==null || abgr==null || width<1 || height<1 || width>256 || height>256
                || (long)width*height!=abgr.length)return null;
        if(sprite.atlas()==null || sprite.atlas().isEmpty() || sprite.id()==null || sprite.id().isEmpty())return null;
        float[] bounds={sprite.minU(),sprite.maxU(),sprite.minV(),sprite.maxV()};
        for(float v:bounds)if(!Float.isFinite(v) || v<0 || v>1)return null;
        if(bounds[0]>=bounds[1] || bounds[2]>=bounds[3])return null;
        for(int value:abgr)if((value>>>24)!=255)return null;
        return new Snapshot(sprite,width,height,abgr.clone());
    }
}
