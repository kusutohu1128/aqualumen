package dev.aqualumen.physics;

public final class ReceiverTextureTest {
    static void require(boolean value,String message) {if(!value)throw new AssertionError(message);}
    public static void main(String[] args) {
        var face=ReceiverFaceTest.decode(ReceiverFaceTest.top());
        int[] pixels={0xff030201,0xff060504,0xff090807,0xff0c0b0a};
        var snapshot=ReceiverTexture.capture(ReceiverFaceTest.SPRITE,2,2,pixels,false);
        // UP uses s=z / t=x; actual quad mapping maps t to U and s to V.
        require(snapshot!=null && snapshot.sample(face,.75,.25).equals(new ReceiverTexture.Sample(0,1,7,8,9,255)),
                "Actual world-face UV must sample top-first native ABGR as unshaded RGBA codes");
        System.out.println("PASS world-face atlas UV / top-first ABGR channel sampling");
        pixels[2]=0xffffffff;
        require(snapshot.sample(face,.75,.25).equals(new ReceiverTexture.Sample(0,1,7,8,9,255)),
                "Snapshot must survive later source image changes/reload without borrowed texel memory");
        System.out.println("PASS texture snapshot immutable ownership");
        require(ReceiverTexture.capture(ReceiverFaceTest.SPRITE,2,2,pixels,true)==null,
                "An unqualified animated sprite must not be promoted as a static material source");
        System.out.println("PASS animated sprite remains unready");
        int[] alpha=pixels.clone();alpha[3]=0xfeffffff;
        require(ReceiverTexture.capture(ReceiverFaceTest.SPRITE,2,2,alpha,false)==null,
                "Partial texture opacity anywhere cannot qualify an opaque full-face source");
        System.out.println("PASS partial texture opacity remains unready");
        int[] large=new int[257];java.util.Arrays.fill(large,0xffffffff);
        require(ReceiverTexture.capture(ReceiverFaceTest.SPRITE,257,1,large,false)==null,
                "Unbounded texture input must remain unsupported before copying");
        System.out.println("PASS bounded static texture capture");
        var malformed=new ReceiverFace.Sprite("atlas","sprite",Float.NaN,1,0,1);
        require(ReceiverTexture.capture(malformed,2,2,pixels,false)==null,
                "Unknown/nonfinite atlas extent cannot be a ready source");
        System.out.println("PASS finite atlas descriptor capture");
        var bogus=new ReceiverFace.Face(face.axis(),face.sign(),face.sprite(),new ReceiverFace.UV(1,1),
                face.alongS(),face.alongT(),face.vertexColor(),face.tint(),face.shade(),face.skyLight(),face.blockLight(),face.vanillaBrightness());
        require(snapshot.sample(bogus,.5,.5)==null,"Out-of-sprite UV must not borrow a clamped edge color");
        System.out.println("PASS out-of-sprite source remains unready");
        require(snapshot.width()==2 && snapshot.height()==2 && snapshot.rgbaSHA256().equals("60095e8c93bdb6d7cd09508d4410ce5b24f669de72bbd064f26bd67152fd5be1"),
                "Top-row-first immutable RGBA bytes must have reproducible evidence identity");
        require(snapshot.sample(face,0,0).equals(new ReceiverTexture.Sample(0,0,1,2,3,255))
                && snapshot.sample(face,1,1).equals(new ReceiverTexture.Sample(1,1,10,11,12,255)),
                "Declared nearest mip0 sampling must own both closed unit-face edges");
        require(ReceiverTexture.capture(ReceiverFaceTest.SPRITE,2,2,new int[3],false)==null
                && ReceiverTexture.capture(ReceiverFaceTest.SPRITE,0,2,new int[0],false)==null,
                "Shape-invalid textures must remain unready");
        var changedSprite=new ReceiverFace.Sprite(ReceiverFaceTest.SPRITE.atlas(),ReceiverFaceTest.SPRITE.id(),0,.5f,0,.5f);
        var changedFace=new ReceiverFace.Face(face.axis(),face.sign(),changedSprite,face.origin(),face.alongS(),face.alongT(),
                face.vertexColor(),face.tint(),face.shade(),face.skyLight(),face.blockLight(),face.vanillaBrightness());
        require(snapshot.sample(changedFace,.5,.5)==null,"Changed atlas descriptor must not pair old texels with new UV");
        try{snapshot.sample(face,Double.NaN,.5);throw new AssertionError("Nonfinite coordinate accepted");}
        catch(IllegalArgumentException expected){}
        System.out.println("PASS RGBA digest / closed-edge / shape / atlas-identity / finite guards");
    }
}
