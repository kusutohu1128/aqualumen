package dev.aqualumen.physics;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.zip.ZipFile;
import javax.imageio.ImageIO;

/** Offline association of sealed terrain/rays and actual face records. Not a live frame. */
public final class ReceiverSurfaceSavedReplay {
    public static void main(String[] args) throws Exception {
        var lines=Files.readAllLines(Path.of(args[0]));
        int[] b=Arrays.stream(lines.get(0).split("\t")).mapToInt(Integer::parseInt).toArray();
        var bounds=new ReceiverField.Bounds(b[0],b[1],b[2],b[3],b[4],b[5]);
        var cells=new HashMap<String,ReceiverField.Cell>();
        for(var line:lines.subList(1,lines.size())) {
            var p=line.split("\t");
            if(cells.put(p[0]+","+p[1]+","+p[2],new ReceiverField.Cell(ReceiverField.Kind.valueOf(p[3]),p[4]))!=null)
                throw new AssertionError("Duplicate saved cell");
        }
        if(cells.size()!=bounds.width()*bounds.height()*bounds.depth())throw new AssertionError("Incomplete saved field");
        var geometry=ReceiverField.capture(new ReceiverField.World() {
            public boolean loaded(int x,int z){return true;}
            public int minY(){return -64;}
            public int maxY(){return 320;}
            public ReceiverField.Cell receiverCell(int x,int y,int z){return Objects.requireNonNull(cells.get(x+","+y+","+z));}
        },bounds);
        int[] abgr;
        try(var jar=new ZipFile(args[3]);var input=jar.getInputStream(jar.getEntry("assets/minecraft/textures/block/sand.png"))) {
            var image=ImageIO.read(input);
            if(image==null || image.getWidth()!=16 || image.getHeight()!=16)throw new AssertionError("Stock decoder shape changed");
            abgr=new int[256];
            for(int y=0;y<16;y++)for(int x=0;x<16;x++) {
                int argb=image.getRGB(x,y);
                abgr[y*16+x]=(argb&0xff00ff00)|((argb>>>16)&255)|((argb&255)<<16);
            }
        }
        var surfaces=new ArrayList<ReceiverSurface.Surface>();
        var textures=new HashMap<ReceiverFace.Sprite,ReceiverTexture.Snapshot>();
        for(var line:Files.readAllLines(Path.of(args[1]))) {
            var p=line.split("\t");
            if(p.length!=29)throw new AssertionError("Saved actual descriptor shape changed");
            var sprite=new ReceiverFace.Sprite(p[6],p[7],Float.parseFloat(p[8]),Float.parseFloat(p[9]),Float.parseFloat(p[10]),Float.parseFloat(p[11]));
            var face=new ReceiverFace.Face(Integer.parseInt(p[3]),Integer.parseInt(p[4]),sprite,
                    new ReceiverFace.UV(Double.parseDouble(p[12]),Double.parseDouble(p[13])),
                    new ReceiverFace.UV(Double.parseDouble(p[14]),Double.parseDouble(p[15])),
                    new ReceiverFace.UV(Double.parseDouble(p[16]),Double.parseDouble(p[17])),
                    new ReceiverFace.Color(Float.parseFloat(p[18]),Float.parseFloat(p[19]),Float.parseFloat(p[20])),
                    new ReceiverFace.Color(Float.parseFloat(p[21]),Float.parseFloat(p[22]),Float.parseFloat(p[23])),
                    Boolean.parseBoolean(p[24]),Integer.parseInt(p[25]),Integer.parseInt(p[26]),Float.parseFloat(p[27]));
            var texture=textures.computeIfAbsent(sprite,s->ReceiverTexture.capture(s,16,16,abgr,false));
            if(texture==null || !texture.rgbaSHA256().equals(p[28]))throw new AssertionError("Full stock pixels differ from actual NativeImage digest");
            surfaces.add(new ReceiverSurface.Surface(Integer.parseInt(p[0]),Integer.parseInt(p[1]),Integer.parseInt(p[2]),p[5],face,texture));
        }
        if(surfaces.size()!=14)throw new AssertionError("Expected14 distinct requested faces");
        // This is an explicit offline stamp, not proof of contemporaneous live captures.
        var stamp=new ReceiverSurface.Stamp(UUID.fromString("b22dbccb-2970-41e6-847f-f183b1ec923d"),"minecraft:overworld",490,0);
        var snapshot=ReceiverSurface.capture(geometry,stamp,surfaces);
        int count=0;
        for(var line:Files.readAllLines(Path.of(args[2]))) {
            var p=line.split("\t");
            if(p.length!=21)throw new AssertionError("Expected ray/first-object plus actual sparse texel");
            var result=snapshot.firstSample(stamp,new ReceiverField.Vec(Double.parseDouble(p[1]),Double.parseDouble(p[2]),Double.parseDouble(p[3])),
                    new ReceiverField.Vec(Double.parseDouble(p[4]),Double.parseDouble(p[5]),Double.parseDouble(p[6])),48);
            var hit=result.geometry();
            var expected=new ReceiverTexture.Sample(Integer.parseInt(p[15]),Integer.parseInt(p[16]),Integer.parseInt(p[17]),
                    Integer.parseInt(p[18]),Integer.parseInt(p[19]),Integer.parseInt(p[20]));
            if(result.status()!=ReceiverSurface.Status.PIXEL || hit.status()!=ReceiverField.Status.HIT
                    || hit.x()!=Integer.parseInt(p[7]) || hit.y()!=Integer.parseInt(p[8]) || hit.z()!=Integer.parseInt(p[9])
                    || Math.abs(hit.travel()-Double.parseDouble(p[10]))>1e-10 || !hit.cell().blockId().equals(p[11])
                    || hit.normal().x()!=Double.parseDouble(p[12]) || hit.normal().y()!=Double.parseDouble(p[13])
                    || hit.normal().z()!=Double.parseDouble(p[14]) || !result.pixel().equals(expected))
                throw new AssertionError("Wrong first-face texel: "+p[0]+" => "+result);
            System.out.println(p[0]+"\t"+hit.x()+"\t"+hit.y()+"\t"+hit.z()+"\t"+expected);
            count++;
        }
        if(count!=16)throw new AssertionError("Expected16 original refracted receiver points");
        System.out.println("PASS16 saved original rays / actual face metadata / independently decoded actual-digest stock texels; offline only");
    }
}
