package dev.aqualumen.physics;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Public geometry/face/texel joining; only the external game world is substituted. */
public final class ReceiverSurfaceTest {
    static final ReceiverSurface.Stamp STAMP=new ReceiverSurface.Stamp(
            UUID.fromString("b22dbccb-2970-41e6-847f-f183b1ec923d"),"minecraft:overworld",490,1);
    static void require(boolean value,String message) {if(!value)throw new AssertionError(message);}
    static ReceiverField.Snapshot geometry() {
        return ReceiverField.capture(new ReceiverFieldTest.Scene(),new ReceiverField.Bounds(-4,-2,-4,8,6,8));
    }
    static ReceiverSurface.Surface sand(int y) {
        var face=ReceiverFaceTest.decode(ReceiverFaceTest.top());
        var texture=ReceiverTexture.capture(face.sprite(),2,2,new int[]{0xff030201,0xff060504,0xff090807,0xff0c0b0a},false);
        return new ReceiverSurface.Surface(-2,y,-3,"minecraft:sand",face,texture);
    }
    static ReceiverSurface.Result sample(ReceiverSurface.Snapshot snapshot,ReceiverSurface.Stamp stamp) {
        return snapshot.firstSample(stamp,new ReceiverField.Vec(-1.75,1.4,-2.25),new ReceiverField.Vec(0,-1,0),48);
    }
    public static void main(String[] args) {
        var snapshot=ReceiverSurface.capture(geometry(),STAMP,List.of(sand(-1)));
        var result=sample(snapshot,STAMP);
        require(result.status()==ReceiverSurface.Status.PIXEL && result.geometry().y()==-1
                && result.geometry().cell().blockId().equals("minecraft:sand")
                && result.pixel().equals(new ReceiverTexture.Sample(0,1,7,8,9,255)),
                "Exact first face must sample its own world-local texture, without a camera-visible proxy");
        System.out.println("PASS exact first-object world-face texel association");
        var stale=new ReceiverSurface.Stamp(STAMP.world(),STAMP.dimension(),STAMP.frame()+1,STAMP.atlasRevision());
        var changed=sample(snapshot,stale);
        require(changed.status()==ReceiverSurface.Status.STALE && changed.geometry()==null && changed.pixel()==null,
                "Old texels must not be reused under a different render frame token");
        System.out.println("PASS frame-scoped stale snapshot rejection");
        var sand=sand(-1);
        var wrong=new ReceiverSurface.Surface(sand.x(),sand.y(),sand.z(),"minecraft:stone",sand.face(),sand.texture());
        var wrongBlock=sample(ReceiverSurface.capture(geometry(),STAMP,List.of(wrong)),STAMP);
        require(wrongBlock.status()==ReceiverSurface.Status.GEOMETRY_ONLY && wrongBlock.geometry().y()==-1 && wrongBlock.pixel()==null,
                "Material for a different block cannot supply the actual first sand receiver");
        System.out.println("PASS first-object block identity qualification");
        var otherTexture=ReceiverTexture.capture(sand.face().sprite(),1,1,new int[]{0xff00ff00},false);
        var conflicting=new ReceiverSurface.Surface(sand.x(),sand.y(),sand.z(),sand.blockId(),sand.face(),otherTexture);
        try {
            ReceiverSurface.capture(geometry(),STAMP,List.of(sand,conflicting));
            throw new AssertionError("Ambiguous same-face sources must not be resolved by last-entry color");
        } catch(IllegalArgumentException expected) {}
        System.out.println("PASS ambiguous duplicate face source rejection");
        var oversized=new ArrayList<ReceiverSurface.Surface>();
        for(int i=0;i<4097;i++)oversized.add(new ReceiverSurface.Surface(i,-1,-3,"minecraft:sand",sand.face(),sand.texture()));
        try {
            ReceiverSurface.capture(geometry(),STAMP,oversized);
            throw new AssertionError("Surface catalogs must reject more than4096 inputs before copying");
        } catch(IllegalArgumentException expected) {}
        System.out.println("PASS bounded face catalog capacity");
        var largeTextures=new ArrayList<ReceiverSurface.Surface>();
        var pixels=new int[256*256];java.util.Arrays.fill(pixels,0xffffffff);
        for(int i=0;i<17;i++)largeTextures.add(new ReceiverSurface.Surface(i-4,-1,-3,"minecraft:sand",sand.face(),
                ReceiverTexture.capture(sand.face().sprite(),256,256,pixels,false)));
        try {
            ReceiverSurface.capture(geometry(),STAMP,largeTextures);
            throw new AssertionError("Unique retained textures must be bounded to1048576 texels");
        } catch(IllegalArgumentException expected) {}
        System.out.println("PASS bounded retained texture memory");
        var nearGeometry=ReceiverField.capture(new ReceiverFieldTest.Scene() {
            @Override public ReceiverField.Cell receiverCell(int x,int y,int z) {
                return y==0?new ReceiverField.Cell(ReceiverField.Kind.OPAQUE,"minecraft:stone"):super.receiverCell(x,y,z);
            }
        },geometry().bounds);
        var nearUnready=new ReceiverSurface.Surface(-2,0,-3,"minecraft:stone",sand.face(),null);
        var near=sample(ReceiverSurface.capture(nearGeometry,STAMP,List.of(nearUnready,sand)),STAMP);
        require(near.status()==ReceiverSurface.Status.GEOMETRY_ONLY && near.geometry().y()==0
                && near.geometry().cell().blockId().equals("minecraft:stone") && near.pixel()==null,
                "An unready near-first stone cannot borrow the farther available sand texture");
        var missing=sample(ReceiverSurface.capture(geometry(),STAMP,List.of(sand(-2))),STAMP);
        require(missing.status()==ReceiverSurface.Status.GEOMETRY_ONLY && missing.geometry().y()==-1 && missing.pixel()==null,
                "Missing exact first face cannot be filled by a farther catalog entry");
        var opposite=new ReceiverFace.Face(sand.face().axis(),-1,sand.face().sprite(),sand.face().origin(),sand.face().alongS(),
                sand.face().alongT(),sand.face().vertexColor(),sand.face().tint(),true,15,0,1);
        var wrongFace=new ReceiverSurface.Surface(-2,-1,-3,"minecraft:sand",opposite,sand.texture());
        require(sample(ReceiverSurface.capture(geometry(),STAMP,List.of(wrongFace)),STAMP).pixel()==null,
                "Same cell's opposite surface must not be substituted for the first entry face");
        System.out.println("PASS unready near-first / missing first / exact normal ownership");
        for(var token:List.of(new ReceiverSurface.Stamp(UUID.randomUUID(),STAMP.dimension(),STAMP.frame(),STAMP.atlasRevision()),
                new ReceiverSurface.Stamp(STAMP.world(),"minecraft:the_nether",STAMP.frame(),STAMP.atlasRevision()),
                new ReceiverSurface.Stamp(STAMP.world(),STAMP.dimension(),STAMP.frame(),STAMP.atlasRevision()+1))) {
            require(sample(snapshot,token).status()==ReceiverSurface.Status.STALE,"Other world/dimension/atlas must invalidate the catalog");
        }
        require(sample(snapshot,null).status()==ReceiverSurface.Status.STALE,"Missing caller token cannot qualify freshness");
        var borrowed=new ArrayList<>(List.of(sand));
        var owned=ReceiverSurface.capture(geometry(),STAMP,borrowed);borrowed.clear();
        require(sample(owned,STAMP).pixel().equals(result.pixel()),"Capture must not retain caller's mutable catalog list");
        var largeShared=new ArrayList<ReceiverSurface.Surface>();
        for(int i=0;i<4096;i++)largeShared.add(new ReceiverSurface.Surface(i,-1,-3,"minecraft:sand",sand.face(),largeTextures.get(0).texture()));
        require(ReceiverSurface.capture(geometry(),STAMP,largeShared)!=null,"Shared immutable texture counted once;4096-face bound is inclusive");
        require(ReceiverSurface.capture(geometry(),STAMP,largeTextures.subList(0,16))!=null,"1048576-texel bound is inclusive");
        System.out.println("PASS full token scope / immutable catalog / shared texture capacity");
        var tied=owned.firstSample(STAMP,new ReceiverField.Vec(-2,1.4,-2.25),new ReceiverField.Vec(0,-1,0),48);
        require(tied.status()==ReceiverSurface.Status.GEOMETRY_ONLY && tied.geometry().status()==ReceiverField.Status.EDGE_TIE && tied.pixel()==null,
                "Ambiguous voxel ownership remains geometry-only, even with an available material");
        var unknown=ReceiverField.capture(new ReceiverFieldTest.Scene() {
            @Override public boolean loaded(int x,int z) {return false;}
        },geometry().bounds);
        var unknownResult=sample(ReceiverSurface.capture(unknown,STAMP,List.of(sand)),STAMP);
        require(unknownResult.status()==ReceiverSurface.Status.GEOMETRY_ONLY && unknownResult.geometry().status()==ReceiverField.Status.UNKNOWN,
                "Material cannot promote unloaded geometry");
        System.out.println("PASS geometry unknown / boundary ambiguity is never material readiness");
    }
}
