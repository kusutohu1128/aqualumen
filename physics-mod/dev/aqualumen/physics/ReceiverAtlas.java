package dev.aqualumen.physics;

/** Immutable RGBA8 atlas readback, not filtered samples or shaded radiance. */
public final class ReceiverAtlas {
    private ReceiverAtlas() {}
    public static boolean rgba8Storage(int format,int[] bits,int[] types) {
        if((format!=0x8058 && format!=0x1908) || bits==null || types==null || bits.length!=4 || types.length!=4)return false;
        for(int i=0;i<4;i++)if(bits[i]!=8 || types[i]!=0x8c17)return false;
        return true;
    }
    public static final class Snapshot {
        private final int width,height;
        private final byte[] rgba;
        private Snapshot(int width,int height,byte[] rgba) {this.width=width;this.height=height;this.rgba=rgba;}
        public ReceiverTexture.Snapshot sprite(ReceiverFace.Sprite sprite,int w,int h) {
            if(sprite==null || w<1 || h<1 || w>256 || h>256)return null;
            double[] bounds={sprite.minU()*(double)width,sprite.maxU()*(double)width,
                    sprite.minV()*(double)height,sprite.maxV()*(double)height};
            for(double v:bounds)if(!Double.isFinite(v) || Math.abs(v-Math.rint(v))>1e-5)return null;
            int x=Math.round(sprite.minU()*width),y=Math.round(sprite.minV()*height);
            if(x<0 || y<0 || (long)x+w>width || (long)y+h>height
                    || Math.round(bounds[1])-x!=w || Math.round(bounds[3])-y!=h)return null;
            int[] pixels=new int[w*h];
            for(int j=0;j<h;j++)for(int i=0;i<w;i++) {
                int offset=((y+j)*width+x+i)*4,value=0;
                for(int c=0;c<4;c++)value|=(rgba[offset+c]&255)<<(8*c);
                pixels[j*w+i]=value;
            }
            return ReceiverTexture.capture(sprite,w,h,pixels,false);
        }
    }
    public static Snapshot capture(int width,int height,byte[] rgba) {
        if(width<1 || height<1 || width>2048 || height>2048 || rgba==null || (long)width*height*4!=rgba.length)return null;
        return new Snapshot(width,height,rgba.clone());
    }
}
