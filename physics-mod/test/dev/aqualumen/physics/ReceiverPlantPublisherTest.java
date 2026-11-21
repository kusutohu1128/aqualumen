package dev.aqualumen.physics;

import java.util.List;
import java.util.HashSet;

public final class ReceiverPlantPublisherTest {
    private static void check(boolean condition) {
        if(!condition)throw new AssertionError("Plant publication transaction mismatch");
    }
    private static void rejected(Runnable action) {
        try { action.run();throw new AssertionError("Unsafe plant publication admitted"); }
        catch(IllegalArgumentException | IllegalStateException expected) {}
    }
    public static void main(String[] arguments) {
        var epoch=new ReceiverRadianceVolume.Epoch(new Object(),1,1);
        var quad=new ReceiverQuadIntersection.Quad(
                new ReceiverQuadIntersection.Point(.1,.1,.5,0,0),new ReceiverQuadIntersection.Point(.9,.1,.5,1,0),
                new ReceiverQuadIntersection.Point(.9,.9,.5,1,1),new ReceiverQuadIntersection.Point(.1,.9,.5,0,1),
                (textureU,textureV)->ReceiverQuadIntersection.Coverage.UNKNOWN);
        var packet=ReceiverPlantPacket.capture(epoch,List.of(quad),0,0,0,true);
        var index=ReceiverPlantCellIndex.capture(packet,new ReceiverPlantCellIndex.Window(0,0,0,1,1,1),epoch,100);
        var cells=ReceiverPlantCellPublication.capture(index,epoch,new ReceiverPlantCellPublication.World() {
            public ReceiverRadianceVolume.Epoch epoch() { return epoch; }
            public void beginValidation() {}
            public ReceiverPlantCellPublication.Proof proof(int x,int y,int z) { return null; }
        });
        ReceiverRadianceVolume.Epoch[] now={epoch};
        int[] calls={0},failure={-1},drift={-1};
        var live=new HashSet<Integer>();
        var publisher=new ReceiverPlantPublisher(new ReceiverRadiancePublisher.Upload() {
            public int create(int width,int height,float[] pixels) {
                if(++calls[0]==failure[0])throw new IllegalStateException("Injected upload failure");
                check(width*height*4==pixels.length);
                live.add(calls[0]);
                if(calls[0]==drift[0])now[0]=new ReceiverRadianceVolume.Epoch(epoch.world(),2,1);
                return calls[0];
            }
            public void delete(int texture) { check(live.remove(texture)); }
        },()->now[0]);
        publisher.publish(packet,cells);check(publisher.ready() && live.size()==3);
        check(publisher.packet()==packet && publisher.publication()==cells && publisher.texture(2)>0);
        now[0]=new ReceiverRadianceVolume.Epoch(epoch.world(),1,2);
        check(!publisher.ready() && publisher.texture(0)==0 && publisher.packet()==null);
        now[0]=epoch;failure[0]=6;
        rejected(()->publisher.publish(packet,cells));check(!publisher.ready() && live.size()==3);
        failure[0]=-1;drift[0]=9;
        rejected(()->publisher.publish(packet,cells));check(!publisher.ready() && live.size()==3);
        now[0]=epoch;drift[0]=-1;
        var foreign=ReceiverPlantPacket.capture(epoch,List.of(quad),0,0,0,true);
        rejected(()->publisher.publish(foreign,cells));check(live.size()==3);
        publisher.publish(packet,cells);check(publisher.ready() && live.size()==3);
        var vertices=List.of(quad.first(),quad.second(),quad.third(),quad.fourth()).stream()
                .map(point->new ReceiverMaterialTriangle.Vertex(point.x(),point.y(),point.z(),
                        new ReceiverVertexShader.Output((float)point.u(),(float)point.v(),.4f,.8f,.2f,.3f,.5f,1))).toList();
        var materials=List.of(new ReceiverMaterialTriangle(epoch,vertices.get(0),vertices.get(1),vertices.get(2)),
                new ReceiverMaterialTriangle(epoch,vertices.get(0),vertices.get(2),vertices.get(3)));
        var material=ReceiverPlantMaterialPacket.capture(packet,materials,epoch);
        var foreignMaterial=ReceiverPlantMaterialPacket.capture(foreign,materials,epoch);
        rejected(()->publisher.publish(packet,cells,foreignMaterial));check(!publisher.ready() && live.size()==3);
        publisher.publish(packet,cells,material);
        check(publisher.ready() && live.size()==4 && publisher.material()==material && publisher.materialTexture()>0);
        failure[0]=calls[0]+4;
        rejected(()->publisher.publish(packet,cells,material));
        check(!publisher.ready() && live.size()==4 && publisher.materialTexture()==0);
        failure[0]=-1;drift[0]=calls[0]+4;
        rejected(()->publisher.publish(packet,cells,material));check(!publisher.ready() && live.size()==4);
        now[0]=epoch;drift[0]=-1;
        publisher.publish(packet,cells);check(publisher.ready() && live.size()==3 && publisher.materialTexture()==0);
        publisher.close();publisher.close();check(live.isEmpty() && !publisher.ready());
        System.out.println("PASS CPU atomic plant publication: exact packet identity, three textures, partial failure rollback, upload epoch drift, replacement and close; not GL or live binding");
    }
}
