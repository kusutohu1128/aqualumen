import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.StringJoiner;
import java.util.zip.ZipFile;
import javax.imageio.ImageIO;

/** Independent stock PNG decoder; outputs hashes and requested sparse samples, not assets. */
public final class ReceiverTextureAssetReference {
    static String sha(byte[] data) throws Exception {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));}
    public static void main(String[] args) throws Exception {
        byte[] encoded;
        try(var jar=new ZipFile(args[0]);var stream=jar.getInputStream(jar.getEntry("assets/minecraft/textures/block/sand.png"))) {
            encoded=stream.readAllBytes();
        }
        BufferedImage image=ImageIO.read(new ByteArrayInputStream(encoded));
        if(image==null || image.getWidth()!=16 || image.getHeight()!=16)throw new IllegalArgumentException("Pinned stock sand reference shape changed");
        byte[] rgba=new byte[16*16*4];
        for(int y=0;y<16;y++)for(int x=0;x<16;x++) {
            int argb=image.getRGB(x,y),q=(y*16+x)*4;
            rgba[q]=(byte)(argb>>>16);rgba[q+1]=(byte)(argb>>>8);rgba[q+2]=(byte)argb;rgba[q+3]=(byte)(argb>>>24);
        }
        var samples=new StringJoiner(",","[","]");
        for(int i=1;i<args.length;i++) {
            String[] p=args[i].split(":");int x=Integer.parseInt(p[0]),y=Integer.parseInt(p[1]);
            if(x<0 || x>=16 || y<0 || y>=16)throw new IllegalArgumentException("Reference pixel outside declared image");
            int q=(y*16+x)*4;
            samples.add("["+x+","+y+","+(rgba[q]&255)+","+(rgba[q+1]&255)+","+(rgba[q+2]&255)+","+(rgba[q+3]&255)+"]");
        }
        System.out.println("{\"width\":16,\"height\":16,\"decoder\":\"JDK ImageIO / ARGB to top-first RGBA\",\"pngSHA256\":\""+sha(encoded)
                +"\",\"rgbaSHA256\":\""+sha(rgba)+"\",\"samples\":"+samples+"}");
    }
}
