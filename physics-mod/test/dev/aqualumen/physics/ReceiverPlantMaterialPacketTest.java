package dev.aqualumen.physics;

import java.util.List;

public final class ReceiverPlantMaterialPacketTest {
    private static ReceiverMaterialTriangle.Vertex vertex(double x,double y,double u,double v,float red) {
        return new ReceiverMaterialTriangle.Vertex(x,y,0,new ReceiverVertexShader.Output((float)u,(float)v,.4f,.8f,red,.5f,.7f,1));
    }
    public static void main(String[] arguments) {
        var epoch=new ReceiverRadianceVolume.Epoch(new Object(),3,1);
        var first=vertex(0,0,0,0,.2f);var second=vertex(1,0,1,0,.4f);
        var third=vertex(1,1,1,1,.6f);var fourth=vertex(0,1,0,1,.8f);
        var quad=new ReceiverQuadIntersection.Quad(new ReceiverQuadIntersection.Point(0,0,0,0,0),
                new ReceiverQuadIntersection.Point(1,0,0,1,0),new ReceiverQuadIntersection.Point(1,1,0,1,1),
                new ReceiverQuadIntersection.Point(0,1,0,0,1),(u,v)->ReceiverQuadIntersection.Coverage.OPAQUE);
        var geometry=ReceiverPlantPacket.capture(epoch,List.of(quad),0,0,0,true);
        var triangles=List.of(new ReceiverMaterialTriangle(epoch,first,second,third),
                new ReceiverMaterialTriangle(epoch,first,third,fourth));
        var packet=ReceiverPlantMaterialPacket.capture(geometry,triangles,epoch);
        float[] values=packet.attributes(epoch);
        if(values.length!=48 || values[4]!=.2f || values[12]!=.4f || values[44]!=.8f
                || values[2]!=.4f || values[3]!=.8f || !packet.owns(geometry)
                || packet.owns(ReceiverPlantPacket.capture(epoch,List.of(quad),0,0,0,true)))
            throw new AssertionError("Material packet layout/order/association changed");
        values[4]=99;if(packet.attributes(epoch)[4]!=.2f)throw new AssertionError("Material storage exposed");
        float[] actual=packet.attributes(epoch);
        for(int primitive=0;primitive<triangles.size();primitive++)for(int corner=0;corner<3;corner++) {
            var expected=triangles.get(primitive).sample(corner==0?1:0,corner==1?1:0,corner==2?1:0,false).attributes();
            float[] channels={expected.u(),expected.v(),expected.block(),expected.sky(),expected.red(),expected.green(),expected.blue(),expected.ao()};
            for(int channel=0;channel<channels.length;channel++)
                if(actual[primitive*24+corner*8+channel]!=channels[channel])
                    throw new AssertionError("Material channel or corner order changed");
        }
        var foreignWorld=new ReceiverRadianceVolume.Epoch(new Object(),epoch.frame(),epoch.resources());
        var replacedResources=new ReceiverRadianceVolume.Epoch(epoch.world(),epoch.frame(),epoch.resources()+1);
        rejects(()->packet.attributes(foreignWorld));
        rejects(()->packet.attributes(replacedResources));
        rejects(()->ReceiverPlantMaterialPacket.capture(geometry,triangles,foreignWorld));
        rejects(()->ReceiverPlantMaterialPacket.capture(geometry,triangles,replacedResources));
        var stale=new ReceiverRadianceVolume.Epoch(epoch.world(),4,1);
        rejects(()->packet.attributes(stale));
        rejects(()->ReceiverPlantMaterialPacket.capture(geometry,triangles,stale));
        rejects(()->ReceiverPlantMaterialPacket.capture(geometry,List.of(triangles.get(1),triangles.get(0)),epoch));
        rejects(()->ReceiverPlantMaterialPacket.capture(geometry,List.of(triangles.get(0)),epoch));
        rejects(()->ReceiverPlantMaterialPacket.capture(geometry,List.of(new ReceiverMaterialTriangle(stale,first,second,third),triangles.get(1)),epoch));
        var anotherGeometry=ReceiverPlantPacket.capture(epoch,List.of(quad),0,0,0,true);
        var alternateFirst=vertex(0,0,0,0,.9f);
        var alternate=ReceiverPlantMaterialPacket.capture(anotherGeometry,List.of(
                new ReceiverMaterialTriangle(epoch,alternateFirst,second,third),
                new ReceiverMaterialTriangle(epoch,alternateFirst,third,fourth)),epoch);
        var regionGeometry=ReceiverPlantPacket.aggregate(epoch,List.of(geometry,anotherGeometry),4096);
        var region=ReceiverPlantMaterialPacket.aggregate(regionGeometry,List.of(packet,alternate),epoch);
        float[] regionValues=region.attributes(epoch);
        if(!region.owns(regionGeometry) || regionValues.length!=96 || regionValues[4]!=.2f || regionValues[52]!=.9f)
            throw new AssertionError("Region material did not retain per-model primitive order and attributes");
        regionValues[52]=0;if(region.attributes(epoch)[52]!=.9f)throw new AssertionError("Aggregate material storage exposed");
        rejects(()->ReceiverPlantMaterialPacket.aggregate(regionGeometry,List.of(packet,packet),epoch));
        rejects(()->ReceiverPlantMaterialPacket.aggregate(regionGeometry,List.of(alternate,packet),epoch));
        rejects(()->ReceiverPlantMaterialPacket.aggregate(regionGeometry,List.of(packet),epoch));
        rejects(()->ReceiverPlantMaterialPacket.aggregate(regionGeometry,List.of(packet,alternate),stale));
        System.out.println("PASS plant material packet: exact geometry/UV/order, all attributes, association, epoch and defensive storage; CPU only");
    }
    private static void rejects(Runnable action) {
        try {action.run();throw new AssertionError("Unsafe plant material packet admitted");}
        catch(IllegalArgumentException | IllegalStateException expected) {}
    }
}
