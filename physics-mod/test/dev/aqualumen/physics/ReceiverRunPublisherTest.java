package dev.aqualumen.physics;

import java.util.HashSet;
import java.util.Set;

public final class ReceiverRunPublisherTest {
    private static void check(boolean condition) { if(!condition)throw new AssertionError("Receiver run transaction mismatch"); }
    public static void main(String[] arguments) {
        var epoch=new ReceiverRadianceVolume.Epoch(new Object(),3,2);
        var layout=ReceiverRunLayout.capture(95,36,95,(x,y,z)->new ReceiverRunLayout.Cell(2,0,0,0));
        var radiance=ReceiverRunRadiance.capture(layout,epoch,index->null);
        var window=new ReceiverRunPublisher.Window(-47,-20,-47,95,36,95);
        Set<Integer> live=new HashSet<>();int[] calls={0},failure={-1};
        var publisher=new ReceiverRunPublisher(new ReceiverRadiancePublisher.Upload() {
            public int create(int width,int height,float[] pixels) {
                if(++calls[0]==failure[0])throw new IllegalStateException("Injected run upload failure");
                check(width*height*4==pixels.length && width*height<=65536);
                check(width==95 && height==95 || width==256 && height==radiance.height());
                live.add(calls[0]);return calls[0];
            }
            public void delete(int texture) { check(live.remove(texture)); }
        });
        publisher.publish(window,layout,radiance,epoch);
        check(publisher.ready(epoch)==2 && live.size()==6 && publisher.records(epoch)==9025);
        check(publisher.window(epoch).equals(window));
        var stale=new ReceiverRadianceVolume.Epoch(epoch.world(),4,2);
        check(publisher.ready(stale)==0 && publisher.texture(4,stale)==0 && publisher.window(stale)==null);
        failure[0]=12;
        try { publisher.publish(window,layout,radiance,epoch);throw new AssertionError("Partial upload exposed"); }
        catch(IllegalStateException expected) { }
        check(publisher.ready(epoch)==0 && live.size()==6);
        failure[0]=-1;publisher.publish(window,layout,radiance,epoch);check(live.size()==6);
        var other=ReceiverRunLayout.capture(95,36,95,(x,y,z)->new ReceiverRunLayout.Cell(2,0,0,0));
        try { publisher.publish(window,other,radiance,epoch);throw new AssertionError("Foreign geometry admitted"); }
        catch(IllegalArgumentException expected) { }
        check(publisher.ready(epoch)==0 && live.size()==6);
        try { publisher.publish(window,layout,radiance,stale);throw new AssertionError("Stale source admitted"); }
        catch(IllegalArgumentException expected) { }
        publisher.close();publisher.close();check(live.isEmpty());
        System.out.println("PASS six-texture compressed publication: epoch/layout identity, failed last upload rollback, replacement and close; CPU only, not GL or Minecraft binding");
    }
}
