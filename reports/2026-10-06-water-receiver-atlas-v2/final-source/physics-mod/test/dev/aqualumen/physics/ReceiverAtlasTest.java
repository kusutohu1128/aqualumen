package dev.aqualumen.physics;

public final class ReceiverAtlasTest {
    static void require(boolean value,String message){if(!value)throw new AssertionError(message);}
    static final ReceiverFace.Sprite SPRITE=new ReceiverFace.Sprite("atlas","sand",.25f,.75f,.25f,.75f);
    static ReceiverFace.Face face() {
        return new ReceiverFace.Face(1,1,SPRITE,new ReceiverFace.UV(.25,.25),new ReceiverFace.UV(0,.5),new ReceiverFace.UV(.5,0),
                new ReceiverFace.Color(1,1,1),new ReceiverFace.Color(1,1,1),true,15,0,1);
    }
    static byte[] pixels() {
        byte[] rgba=new byte[4*4*4];
        for(int i=0;i<16;i++)rgba[i*4+3]=(byte)255;
        int[][] values={{1,2,3},{4,5,6},{7,8,9},{10,11,12}};
        for(int y=0;y<2;y++)for(int x=0;x<2;x++)for(int c=0;c<3;c++)rgba[((y+1)*4+x+1)*4+c]=(byte)values[y*2+x][c];
        return rgba;
    }
    public static void main(String[] args) {
        var atlas=ReceiverAtlas.capture(4,4,pixels());var texture=atlas.sprite(SPRITE,2,2);
        require(texture!=null && texture.sample(face(),.75,.25).equals(new ReceiverTexture.Sample(0,1,7,8,9,255))
                && texture.rgbaSHA256().equals("60095e8c93bdb6d7cd09508d4410ce5b24f669de72bbd064f26bd67152fd5be1"),
                "Actual atlas rect must preserve increasing GL row order, affine UV and RGBA byte channels");
        System.out.println("PASS exact atlas rectangle / RGBA orientation / whole sprite digest");
        var borrowed=pixels();var owned=ReceiverAtlas.capture(4,4,borrowed);borrowed[((2)*4+1)*4]=(byte)99;
        require(owned.sprite(SPRITE,2,2).sample(face(),.75,.25).red()==7,"Owned atlas must not follow later readback buffer writes");
        System.out.println("PASS atlas immutable readback ownership");
        var fractional=new ReceiverFace.Sprite("atlas","sand",.251f,.75f,.25f,.75f);
        require(atlas.sprite(fractional,2,2)==null,"Fractional or mismatched sprite rectangle must not round onto another pixel owner");
        System.out.println("PASS nonintegral atlas extent remains unsupported");
        require(ReceiverAtlas.capture(2049,1,new byte[2049*4])==null,"Readback dimensions must be bounded before copying");
        System.out.println("PASS bounded atlas capture dimensions");
        require(ReceiverAtlas.capture(4,4,new byte[63])==null && ReceiverAtlas.capture(0,4,new byte[0])==null
                && ReceiverAtlas.capture(4,4,null)==null,"Incomplete/empty atlas must remain unready");
        require(atlas.sprite(SPRITE,1,2)==null,"Texture width must equal actual atlas rectangle width");
        var alpha=pixels();alpha[((2)*4+1)*4+3]=(byte)254;
        require(ReceiverAtlas.capture(4,4,alpha).sprite(SPRITE,2,2)==null,"Nonopaque sprite region cannot qualify opaque material");
        var other=pixels();other[3]=0;
        require(ReceiverAtlas.capture(4,4,other).sprite(SPRITE,2,2)!=null,"Transparent neighboring sprite must not invalidate opaque target");
        require(atlas.sprite(new ReceiverFace.Sprite("atlas","sand",Float.NaN,.75f,.25f,.75f),2,2)==null
                && atlas.sprite(new ReceiverFace.Sprite("atlas","sand",.75f,1.25f,.25f,.75f),2,2)==null,
                "Invalid/outside atlas region cannot borrow pixels");
        System.out.println("PASS exact shape / opacity / neighbor isolation / finite region guards");
        require(ReceiverAtlas.rgba8Storage(0x1908,new int[]{8,8,8,8},new int[]{0x8c17,0x8c17,0x8c17,0x8c17}),
                "Unsized actual RGBA is supported only when all actual channels are8-bit unsigned-normalized");
        System.out.println("PASS queried unsized normalized RGBA8 storage");
        require(!ReceiverAtlas.rgba8Storage(0x1908,new int[]{8,8,8,0},new int[]{0x8c17,0x8c17,0x8c17,0x8c17})
                && !ReceiverAtlas.rgba8Storage(0x8058,new int[]{8,8,8,8},new int[]{0x8c17,0x8c17,0x8c17,0x1406})
                && !ReceiverAtlas.rgba8Storage(0x8c43,new int[]{8,8,8,8},new int[]{0x8c17,0x8c17,0x8c17,0x8c17}),
                "Missing alpha, float or sRGB storage is not silently treated as linear normalized RGBA8");
        System.out.println("PASS unqualified channel type / alpha / sRGB rejection");
    }
}
