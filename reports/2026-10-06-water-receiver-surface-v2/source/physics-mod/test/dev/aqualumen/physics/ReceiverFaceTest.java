package dev.aqualumen.physics;

public final class ReceiverFaceTest {
    static int[] top() {
        int[] data=new int[32];
        float[][] points={{0,1,0,.125f,.25f},{0,1,1,.125f,.5f},{1,1,1,.375f,.5f},{1,1,0,.375f,.25f}};
        for (int i=0;i<4;i++) {
            for (int c=0;c<3;c++) data[i*8+c]=Float.floatToRawIntBits(points[i][c]);
            data[i*8+3]=0xffffffff;
            data[i*8+4]=Float.floatToRawIntBits(points[i][3]);data[i*8+5]=Float.floatToRawIntBits(points[i][4]);
        }
        return data;
    }
    static final ReceiverFace.Sprite SPRITE=new ReceiverFace.Sprite("minecraft:textures/atlas/blocks.png","minecraft:block/sand",.125f,.375f,.25f,.5f);
    static ReceiverFace.Face decode(int[] data) { return ReceiverFace.decode(data,0,1,0,SPRITE,0xffffff,true,15,0,1); }
    static void require(boolean condition,String message) { if(!condition)throw new AssertionError(message); }
    public static void main(String[] args) {
        var face=decode(top());
        // UP's two world axes are z then x; UV orientation must follow actual vertices.
        require(face!=null && face.axis()==1 && face.sign()==1 && face.sprite().id().equals("minecraft:block/sand")
                && face.uvAt(.75,.25).equals(new ReceiverFace.UV(.1875,.4375)),
                "Full face must preserve atlas identity and actual rotated world-to-UV mapping");
        System.out.println("PASS actual full-face atlas UV mapping");
        int[] reversed=top();
        for(int i=0;i<8;i++) {int value=reversed[8+i];reversed[8+i]=reversed[24+i];reversed[24+i]=value;}
        require(decode(reversed)==null,"Opposite winding must not be accepted as the claimed opaque face");
        System.out.println("PASS face orientation ownership");
        int[] partial=top();partial[0]=Float.floatToRawIntBits(.2f);
        require(decode(partial)==null,"Partial face is not a full cube surface");
        int[] invalid=top();invalid[4]=Float.floatToRawIntBits(Float.NaN);
        require(decode(invalid)==null,"Nonfinite atlas coordinate must not be a source");
        int[] warped=top();warped[20]=Float.floatToRawIntBits(.3f);
        require(decode(warped)==null,"Non-affine quad mapping must be unready");
        int[] gradient=top();gradient[11]=0xff80ffff;
        require(decode(gradient)==null,"Unrepresented vertex color gradient must be unready");
        int[] alpha=top();for(int i=0;i<4;i++)alpha[i*8+3]=0x80ffffff;
        require(decode(alpha)==null,"Partial opacity must not become an opaque material source");
        require(decode(new int[36])==null && ReceiverFace.decode(top(),0,1,1,SPRITE,0xffffff,true,15,0,1)==null,
                "Unknown packed layout or non-axis face must be unready");
        int[] data=top();var immutable=decode(data);data[4]=Float.floatToRawIntBits(.9f);
        require(immutable.uvAt(0,0).equals(new ReceiverFace.UV(.125,.25)),"Face must not retain mutable baked vertex data");
        var colored=ReceiverFace.decode(top(),0,1,0,SPRITE,0x804020,false,12,3,.8f);
        require(colored!=null && colored.tint().equals(new ReceiverFace.Color(128/255f,64/255f,32/255f))
                && !colored.shade() && colored.skyLight()==12 && colored.blockLight()==3 && colored.vanillaBrightness()==.8f,
                "Tint and raw lighting metadata must survive without shading or gamma conversion");
        System.out.println("PASS unsupported / finite / opacity / immutable / raw tint-light guards");
    }
}
