package dev.aqualumen.physics;

import java.util.Arrays;
import java.util.Objects;

public final class ReceiverRunPublisher implements AutoCloseable {
    public record Window(int x,int y,int z,int width,int height,int depth) {
        public Window {
            if(width<1 || width>96 || height<1 || height>64 || depth<1 || depth>96
                || (long)x+width>Integer.MAX_VALUE || (long)y+height>Integer.MAX_VALUE || (long)z+depth>Integer.MAX_VALUE)
                throw new IllegalArgumentException("Receiver run window exceeds bounded extent");
        }
    }
    private final ReceiverRadiancePublisher.Upload upload;
    private int[] textures=new int[6];
    private ReceiverRunRadiance radiance;
    private Window window;
    public ReceiverRunPublisher(ReceiverRadiancePublisher.Upload upload) { this.upload=Objects.requireNonNull(upload); }
    public void publish(Window nextWindow,ReceiverRunLayout layout,ReceiverRunRadiance next,ReceiverRadianceVolume.Epoch current) {
        invalidate();
        if(nextWindow==null || layout==null || next==null || !next.current(current) || !next.owns(layout)
            || nextWindow.width()!=layout.width() || nextWindow.height()!=layout.height() || nextWindow.depth()!=layout.depth())
            throw new IllegalArgumentException("Stale or mismatched receiver run publication");
        int[] pending=new int[6];
        float[][] data={next.cells(),next.source(),next.sun(),next.faces(),layout.headers(),
            Arrays.copyOf(layout.ranges(),next.width()*next.height()*4)};
        try {
            for(int index=0;index<pending.length;index++) {
                int width=index==4?nextWindow.width():next.width();
                int height=index==4?nextWindow.depth():next.height();
                int texture=upload.create(width,height,data[index]);
                if(texture<=0)throw new IllegalStateException("Receiver run allocation failed");
                for(int existing:textures)if(existing==texture)throw new IllegalStateException("Upload reused an active run texture");
                for(int previous=0;previous<index;previous++)if(pending[previous]==texture)throw new IllegalStateException("Upload reused a pending run texture");
                pending[index]=texture;
            }
        } catch(RuntimeException error) {
            for(int texture:pending)if(texture!=0)upload.delete(texture);
            throw error;
        }
        int[] previous=textures;textures=pending;radiance=next;window=nextWindow;
        for(int texture:previous)if(texture!=0)upload.delete(texture);
    }
    public int ready(ReceiverRadianceVolume.Epoch now) { return radiance!=null && radiance.current(now)?2:0; }
    public int records(ReceiverRadianceVolume.Epoch now) { return ready(now)==2?radiance.records():0; }
    public int texture(int index,ReceiverRadianceVolume.Epoch now) {
        if(index<0 || index>=6)throw new IllegalArgumentException("Unknown receiver run texture");
        return ready(now)==2?textures[index]:0;
    }
    public Window window(ReceiverRadianceVolume.Epoch now) { return ready(now)==2?window:null; }
    public void invalidate() { radiance=null;window=null; }
    @Override public void close() {
        invalidate();int[] previous=textures;textures=new int[6];
        for(int texture:previous)if(texture!=0)upload.delete(texture);
    }
}
