package dev.aqualumen.physics;

import java.util.Arrays;
import java.util.Objects;

public final class ReceiverRunRadiance {
    public record Sample(ReceiverRadianceVolume.Epoch epoch,int sourceIndex,float[] total,float[] sun,float[] face) {
        public Sample {
            Objects.requireNonNull(epoch);
            total=total.clone();sun=sun.clone();face=face.clone();
            if(sourceIndex<0 || total.length!=4 || sun.length!=4 || face.length!=4)
                throw new IllegalArgumentException("Receiver run source extent invalid");
        }
        @Override public float[] total() { return total.clone(); }
        @Override public float[] sun() { return sun.clone(); }
        @Override public float[] face() { return face.clone(); }
    }
    public interface Sources { Sample sample(int sourceIndex); }
    private final ReceiverRadianceVolume.Epoch epoch;
    private final ReceiverRunLayout layout;
    private final int records;
    private final float[] cells,source,sun,faces;
    private ReceiverRunRadiance(ReceiverRunLayout layout,ReceiverRadianceVolume.Epoch epoch,int records,float[] cells,float[] source,float[] sun,float[] faces) {
        this.layout=layout;
        this.epoch=epoch;this.records=records;this.cells=cells;this.source=source;this.sun=sun;this.faces=faces;
    }
    public static ReceiverRunRadiance capture(ReceiverRunLayout layout,ReceiverRadianceVolume.Epoch epoch,Sources sources) {
        Objects.requireNonNull(layout);Objects.requireNonNull(epoch);Objects.requireNonNull(sources);
        int records=layout.runCount(),length=256*((records+255)/256)*4;
        float[] cells=Arrays.copyOf(layout.geometry(),length),ranges=layout.ranges();
        float[] total=new float[length],sun=new float[length],faces=new float[length];
        for(int index=0;index<records;index++) {
            int offset=index*4;
            if(cells[offset]!=3 || ranges[offset+2]<0)continue;
            int sourceIndex=(int)ranges[offset+2];
            Sample sample=sources.sample(sourceIndex);
            if(sample==null)continue;
            if(sample.sourceIndex()!=sourceIndex || sample.epoch().world()!=epoch.world()
                || sample.epoch().frame()!=epoch.frame() || sample.epoch().resources()!=epoch.resources())
                throw new IllegalStateException("Receiver run source ownership mismatch");
            System.arraycopy(sample.total(),0,total,offset,4);
            System.arraycopy(sample.sun(),0,sun,offset,4);
            System.arraycopy(sample.face(),0,faces,offset,4);
        }
        ReceiverRadianceVolume.validateTables(cells,total,sun,faces);
        return new ReceiverRunRadiance(layout,epoch,records,cells,total,sun,faces);
    }
    public boolean current(ReceiverRadianceVolume.Epoch now) {
        return now!=null && epoch.world()==now.world() && epoch.frame()==now.frame() && epoch.resources()==now.resources();
    }
    public int records() { return records; }
    public boolean owns(ReceiverRunLayout candidate) { return layout==candidate; }
    public int width() { return 256; }
    public int height() { return (records+255)/256; }
    public float[] cells() { return cells.clone(); }
    public float[] source() { return source.clone(); }
    public float[] sun() { return sun.clone(); }
    public float[] faces() { return faces.clone(); }
}
