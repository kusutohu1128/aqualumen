package dev.aqualumen.physics;

public final class ReceiverRunRadianceTest {
    private static void check(boolean condition) {
        if(!condition)throw new AssertionError("Receiver run radiance mismatch");
    }
    private static ReceiverRunRadiance.Sample sample(ReceiverRadianceVolume.Epoch epoch,int sourceIndex) {
        return new ReceiverRunRadiance.Sample(epoch,sourceIndex,new float[]{.75f,.5f,.25f,1},
            new float[]{.1f,.05f,0,1},new float[]{0,1,0,1});
    }
    public static void main(String[] arguments) {
        var epoch=new ReceiverRadianceVolume.Epoch(new Object(),7,2);
        var layout=ReceiverRunLayout.capture(95,36,95,(x,y,z)->new ReceiverRunLayout.Cell(y==10?3:2,0,0,0));
        int[] calls={0};
        var packed=ReceiverRunRadiance.capture(layout,epoch,index->{calls[0]++;return sample(epoch,index);});
        check(calls[0]==95*95 && packed.records()==95*95*3 && packed.source().length==packed.width()*packed.height()*4);
        float[] total=packed.source(),sun=packed.sun(),faces=packed.faces(),ranges=layout.ranges();
        for(int record=0;record<packed.records();record++) {
            int offset=record*4;
            check(total[offset+3]==(ranges[offset+2]>=0?1:0));
            if(ranges[offset+2]>=0)check(total[offset]==.75f && sun[offset]==.1f && faces[offset+1]==1);
        }
        total[7]=0;check(packed.source()[7]==1);
        check(packed.current(epoch));
        check(!packed.current(new ReceiverRadianceVolume.Epoch(epoch.world(),8,2)));
        check(!packed.current(new ReceiverRadianceVolume.Epoch(new Object(),7,2)));
        check(!packed.current(new ReceiverRadianceVolume.Epoch(epoch.world(),7,3)));
        var missing=ReceiverRunRadiance.capture(layout,epoch,index->null);
        for(float value:missing.source())check(value==0);
        var blocked=ReceiverRunLayout.capture(1,4,1,(x,y,z)->new ReceiverRunLayout.Cell(3,0,0,0,false));
        var unlit=ReceiverRunRadiance.capture(blocked,epoch,index->{throw new AssertionError("Blocked run requested a source");});
        check(unlit.records()==1 && unlit.cells()[0]==3 && unlit.source()[3]==0);
        try { ReceiverRunRadiance.capture(layout,epoch,index->sample(epoch,index+1));throw new AssertionError("Reordered source admitted"); }
        catch(IllegalStateException expected) { }
        try { ReceiverRunRadiance.capture(layout,epoch,index->sample(new ReceiverRadianceVolume.Epoch(epoch.world(),8,2),index));throw new AssertionError("Stale source admitted"); }
        catch(IllegalStateException expected) { }
        try { ReceiverRunRadiance.capture(layout,epoch,index->new ReceiverRunRadiance.Sample(epoch,index,
            new float[]{.75f,0,0,1},new float[]{0,0,0,0},new float[]{0,1,0,1}));throw new AssertionError("Unpaired source admitted"); }
        catch(IllegalArgumentException expected) { }
        try { ReceiverRunRadiance.capture(layout,epoch,index->new ReceiverRunRadiance.Sample(epoch,index,
            new float[]{Float.NaN,0,0,1},new float[]{0,0,0,1},new float[]{0,1,0,1}));throw new AssertionError("Nonfinite source admitted"); }
        catch(IllegalArgumentException expected) { }
        System.out.println("PASS packed receiver run radiance: supplied paired channels/address/epoch/defensive ownership and missing/unpaired/nonfinite negatives; CPU only, not live Sodium shading or GPU upload");
    }
}
