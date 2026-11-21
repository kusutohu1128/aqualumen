package dev.aqualumen.physics;

import java.util.Arrays;
import java.util.List;

public final class ReceiverPlantCellIndexTest {
    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }
    private static void rejected(Runnable action) {
        try { action.run(); throw new AssertionError("Unsafe plant index admitted"); }
        catch (IllegalArgumentException | IllegalStateException expected) {}
    }
    public static void main(String[] arguments) {
        var ownerWindow=new ReceiverPlantCellIndex.Window(-43,29,-43,87,36,87);
        check(ownerWindow.expanded(1,-64,320).equals(new ReceiverPlantCellIndex.Window(-44,28,-44,89,38,89)),
                "Owner capture halo includes all neighboring boundary cells");
        check(new ReceiverPlantCellIndex.Window(0,-64,0,3,3,3).expanded(1,-64,320)
                .equals(new ReceiverPlantCellIndex.Window(-1,-64,-1,5,4,5)),"Owner halo clips only world-height boundary");
        rejected(()->ownerWindow.expanded(-1,-64,320));
        rejected(()->ownerWindow.expanded(1,30,320));
        rejected(()->new ReceiverPlantCellIndex.Window(Integer.MIN_VALUE,0,0,1,1,1).expanded(1,-64,320));
        rejected(()->new ReceiverPlantCellIndex.Window(0,0,0,96,1,96).expanded(1,-64,320));
        for(int texels: new int[]{4,6}) {
            int primitiveCount=20001;
            float[] values=new float[primitiveCount*texels*4];
            for(int index=0;index<values.length;index++)values[index]=index;
            var payload=ReceiverPlantPacket.texturePayload(texels,values);
            check(payload.width()==texels*64 && payload.height()==313,"Tiled dimensions retain partial last row");
            float[] tiled=payload.values();
            for(int primitive=0;primitive<primitiveCount;primitive++)
                for(int texel=0;texel<texels;texel++) {
                    int address=((primitive/64)*payload.width()+(primitive%64)*texels+texel)*4;
                    for(int channel=0;channel<4;channel++)
                        check(tiled[address+channel]==values[(primitive*texels+texel)*4+channel],"Exact tiled primitive/channel correspondence");
                }
            for(int index=values.length;index<tiled.length;index++)check(tiled[index]==0,"Zero padding does not invent primitives");
            values[0]=-1;tiled[1]=-1;
            check(payload.values()[0]==0 && payload.values()[1]==1,"Tiled payload defensively owns attributes");
        }
        rejected(()->ReceiverPlantPacket.texturePayload(5,new float[20]));
        rejected(()->ReceiverPlantPacket.texturePayload(4,new float[17]));
        rejected(()->ReceiverPlantPacket.texturePayload(4,new float[131073*16]));
        var epoch = new ReceiverRadianceVolume.Epoch(new Object(),1,1);
        var quad = new ReceiverQuadIntersection.Quad(
                new ReceiverQuadIntersection.Point(100.9,20.1,-5.9,.1,.1),
                new ReceiverQuadIntersection.Point(101.2,20.1,-5.9,.9,.1),
                new ReceiverQuadIntersection.Point(101.2,20.9,-5.1,.9,.9),
                new ReceiverQuadIntersection.Point(100.9,20.9,-5.1,.1,.9),
                (textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
        var packet = ReceiverPlantPacket.capture(epoch,List.of(quad),100,20,-6,true);
        var bounds=packet.bounds(epoch);
        check(Math.abs(bounds.minX()-100.9)<1e-6 && Math.abs(bounds.maxX()-101.2)<1e-6
                && Math.abs(bounds.minY()-20.1)<1e-6 && Math.abs(bounds.maxY()-20.9)<1e-6
                && Math.abs(bounds.minZ()+5.9)<1e-6 && Math.abs(bounds.maxZ()+5.1)<1e-6,
                "Actual world bounds retain cross-owner geometry and negative coordinates");
        rejected(()->packet.bounds(new ReceiverRadianceVolume.Epoch(epoch.world(),2,1)));
        var unqualified = ReceiverPlantPacket.capture(epoch,List.of(quad),100,20,-6,false);
        var aggregate = ReceiverPlantPacket.aggregate(epoch,List.of(packet,unqualified),4);
        check(aggregate.count()==4 && aggregate.triangles()[15]==1 && aggregate.triangles()[47]==0,
                "Aggregation preserves independent alpha qualification and packet order");
        rejected(() -> ReceiverPlantPacket.aggregate(epoch,List.of(packet,packet),4));
        rejected(() -> ReceiverPlantPacket.aggregate(epoch,List.of(packet,unqualified),3));
        rejected(() -> ReceiverPlantPacket.aggregate(epoch,List.of(),4));
        rejected(() -> ReceiverPlantPacket.aggregate(epoch,List.of(packet),131073));
        rejected(() -> ReceiverPlantPacket.aggregate(new ReceiverRadianceVolume.Epoch(epoch.world(),2,1),List.of(packet),4));
        rejected(() -> ReceiverPlantPacket.aggregate(epoch,List.of(packet,
                ReceiverPlantPacket.capture(epoch,List.of(quad),101,20,-6,true)),4));
        var models = new java.util.ArrayList<ReceiverPlantPacket>();
        for (int owner=0;owner<2500;owner++) {
            double ownerX=owner%30, ownerZ=owner/30;
            var leaf = new ReceiverQuadIntersection.Quad(
                    new ReceiverQuadIntersection.Point(ownerX+.1,.1,ownerZ+.5,0,0),
                    new ReceiverQuadIntersection.Point(ownerX+.9,.1,ownerZ+.5,1,0),
                    new ReceiverQuadIntersection.Point(ownerX+.9,.9,ownerZ+.5,1,1),
                    new ReceiverQuadIntersection.Point(ownerX+.1,.9,ownerZ+.5,0,1),
                    (textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
            models.add(ReceiverPlantPacket.capture(epoch,List.of(leaf),0,0,0,owner%2==0));
        }
        var global = ReceiverPlantPacket.aggregate(epoch,models,5000);
        var globalIndex = ReceiverPlantCellIndex.capture(global,
                new ReceiverPlantCellIndex.Window(0,0,0,30,1,84),epoch,5000);
        check(global.count()==5000 && globalIndex.memberships()==5000,"More than 4096 global triangles without per-cell truncation");
        for (int owner=0;owner<2500;owner++) {
            check(Arrays.equals(globalIndex.candidates(owner%30,0,owner/30,epoch),new int[]{owner*2,owner*2+1}),
                    "Stable global primitive addresses for each model");
            check(Arrays.equals(Arrays.copyOfRange(global.triangles(),owner*32,owner*32+32),models.get(owner).triangles()),
                    "Aggregation retains serialized coordinates and UV exactly");
        }
        var window = new ReceiverPlantCellIndex.Window(99,19,-7,5,4,4);
        var index = ReceiverPlantCellIndex.capture(packet,window,epoch,1000);
        check(index.memberships() == 4,"Both triangles cover two neighboring owner cells");
        check(Arrays.equals(index.candidates(100,20,-6,epoch),new int[]{0,1}),"Owner candidates");
        check(Arrays.equals(index.candidates(101,20,-6,epoch),new int[]{0,1}),"Spilled geometry candidates");
        check(index.candidates(99,19,-7,epoch).length == 0,"Known packet empty lookup");
        int[] candidate = index.candidates(101,20,-6,epoch); candidate[0] = -1;
        check(index.candidates(101,20,-6,epoch)[0] == 0,"Immutable candidate membership");
        var selected = packet.select(index.candidates(101,20,-6,epoch));
        check(selected.count() == 2 && selected.current(epoch) && Arrays.equals(selected.triangles(),packet.triangles()),"Subset preserves epoch/coordinates/qualification");
        rejected(() -> packet.select(new int[]{0,0})); rejected(() -> packet.select(new int[]{2}));
        rejected(() -> index.candidates(98,20,-6,epoch));
        rejected(() -> index.candidates(100,20,-6,new ReceiverRadianceVolume.Epoch(epoch.world(),2,1)));
        rejected(() -> index.candidates(100,20,-6,new ReceiverRadianceVolume.Epoch(epoch.world(),1,2)));
        rejected(() -> index.candidates(100,20,-6,new ReceiverRadianceVolume.Epoch(new Object(),1,1)));
        rejected(() -> ReceiverPlantCellIndex.capture(packet,new ReceiverPlantCellIndex.Window(100,20,-6,1,1,1),epoch,1000));
        rejected(() -> ReceiverPlantCellIndex.capture(packet,window,epoch,3));
        float[] triangles = packet.triangles();
        for (int primitive = 0; primitive < packet.count(); primitive++) {
            int offset = primitive*16;
            for (int second = 0; second <= 16; second++)
                for (int third = 0; third <= 16-second; third++) {
                    double middle = second/16.0, last = third/16.0, first = 1-middle-last;
                    int x = (int)Math.floor(packet.x()+triangles[offset]*first+triangles[offset+4]*middle+triangles[offset+8]*last);
                    int y = (int)Math.floor(packet.y()+triangles[offset+1]*first+triangles[offset+5]*middle+triangles[offset+9]*last);
                    int z = (int)Math.floor(packet.z()+triangles[offset+2]*first+triangles[offset+6]*middle+triangles[offset+10]*last);
                    int expected = primitive;
                    check(Arrays.stream(index.candidates(x,y,z,epoch)).anyMatch(value -> value == expected),"All sampled serialized triangle points remain indexed");
                }
        }
        var boundaryQuad = new ReceiverQuadIntersection.Quad(
                new ReceiverQuadIntersection.Point(101,20.2,-5.8,0,0),new ReceiverQuadIntersection.Point(101,20.8,-5.8,1,0),
                new ReceiverQuadIntersection.Point(101,20.8,-5.2,1,1),new ReceiverQuadIntersection.Point(101,20.2,-5.2,0,1),
                (textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
        var boundaryPacket = ReceiverPlantPacket.capture(epoch,List.of(boundaryQuad),100,20,-6,false);
        var boundary = ReceiverPlantCellIndex.capture(boundaryPacket,window,epoch,1000);
        check(boundary.candidates(100,20,-6,epoch).length == 2 && boundary.candidates(101,20,-6,epoch).length == 2,
                "Closed face contacts are indexed on both sides");
        rejected(() -> ReceiverPlantCellIndex.capture(boundaryPacket,new ReceiverPlantCellIndex.Window(101,19,-7,2,4,4),epoch,1000));
        var roundedQuad = new ReceiverQuadIntersection.Quad(
                new ReceiverQuadIntersection.Point(100.999999985,20.2,-5.8,0,0),new ReceiverQuadIntersection.Point(100.999999985,20.8,-5.8,1,0),
                new ReceiverQuadIntersection.Point(100.999999985,20.8,-5.2,1,1),new ReceiverQuadIntersection.Point(100.999999985,20.2,-5.2,0,1),
                (textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
        var roundedPacket = ReceiverPlantPacket.capture(epoch,List.of(roundedQuad),100,20,-6,true);
        check(roundedPacket.triangles()[0] == 1,"Fixture actually rounds to the GPU voxel boundary");
        var rounded = ReceiverPlantCellIndex.capture(roundedPacket,window,epoch,1000);
        check(rounded.candidates(100,20,-6,epoch).length == 2 && rounded.candidates(101,20,-6,epoch).length == 2,
                "Membership follows uploaded float geometry rather than pre-serialization doubles");
        rejected(() -> index.candidates(Integer.MAX_VALUE,20,-6,epoch));
        var water = new ReceiverWaterVolume.Observation(true,"minecraft:water","water",true,1,true);
        var column = List.of(water,water,water);
        var proof = new ReceiverPlantCellPublication.World() {
            public ReceiverRadianceVolume.Epoch epoch() { return epoch; }
            public void beginValidation() {}
            public ReceiverPlantCellPublication.Proof proof(int x,int y,int z) {
                if (x == 99) return null;
                if (x == 100) return new ReceiverPlantCellPublication.Proof(column,false);
                return new ReceiverPlantCellPublication.Proof(column,true);
            }
        };
        var publication = ReceiverPlantCellPublication.capture(index,epoch,proof);
        float[] headers = publication.headers(epoch), links = publication.indices(epoch);
        for (int y=0;y<window.height();y++) for (int z=0;z<window.depth();z++) for (int x=0;x<window.width();x++) {
            int cell = x+window.width()*(y*window.depth()+z);
            int[] expected = index.candidates(window.x()+x,window.y()+y,window.z()+z,epoch);
            check(headers[cell*4+1] == expected.length,"Every serialized cell count matches authoritative membership");
            for (int member=0;member<expected.length;member++)
                check(links[((int)headers[cell*4]+member)*4] == expected[member],"Original primitive IDs survive publication");
            check(headers[cell*4+2] == (x==0?0:1) && headers[cell*4+3] == (x<2?0:1),
                    "Fluid and model completeness remain independently qualified");
        }
        headers[0] = -1; links[0] = -1;
        check(publication.headers(epoch)[0] >= 0 && publication.indices(epoch)[0] >= 0,"Publication output cannot mutate owned arrays");
        rejected(() -> publication.headers(new ReceiverRadianceVolume.Epoch(epoch.world(),2,1)));
        int[] calls = {0};
        var drifting = new ReceiverPlantCellPublication.World() {
            public void beginValidation() {}
            public ReceiverRadianceVolume.Epoch epoch() {
                return calls[0] == 0 ? epoch : new ReceiverRadianceVolume.Epoch(epoch.world(),epoch.frame(),epoch.resources()+1);
            }
            public ReceiverPlantCellPublication.Proof proof(int x,int y,int z) { calls[0]++; return new ReceiverPlantCellPublication.Proof(column,true); }
        };
        rejected(() -> ReceiverPlantCellPublication.capture(index,epoch,drifting));
        for (boolean fluidChange : new boolean[]{true,false}) {
            var changed = new ReceiverPlantCellPublication.World() {
                private boolean validating;
                public ReceiverRadianceVolume.Epoch epoch() { return epoch; }
                public void beginValidation() { validating = true; }
                public ReceiverPlantCellPublication.Proof proof(int x,int y,int z) {
                    return new ReceiverPlantCellPublication.Proof(validating && fluidChange ? List.of() : column,
                            !(validating && !fluidChange));
                }
            };
            rejected(() -> ReceiverPlantCellPublication.capture(index,epoch,changed));
        }
        System.out.println("PASS plant cell index CPU: spill, closed boundary, serialized geometry coverage, immutable subsets, epoch/extent/capacity negatives; not water qualification or live DDA");
    }
}
