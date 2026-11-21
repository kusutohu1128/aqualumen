package dev.aqualumen.physics;

import java.util.Objects;
import java.util.function.Supplier;

public final class ReceiverPlantPublisher implements AutoCloseable {
    private final ReceiverRadiancePublisher.Upload upload;
    private final Supplier<ReceiverRadianceVolume.Epoch> epoch;
    private int[] textures=new int[3];
    private ReceiverPlantPacket packet;
    private ReceiverPlantCellPublication publication;
    private ReceiverPlantMaterialPacket material;
    public ReceiverPlantPublisher(ReceiverRadiancePublisher.Upload upload, Supplier<ReceiverRadianceVolume.Epoch> epoch) {
        this.upload=Objects.requireNonNull(upload);this.epoch=Objects.requireNonNull(epoch);
    }
    public void publish(ReceiverPlantPacket next, ReceiverPlantCellPublication cells) {
        publish(next,cells,null);
    }
    public void publish(ReceiverPlantPacket next, ReceiverPlantCellPublication cells,ReceiverPlantMaterialPacket attributes) {
        invalidate();
        var now=epoch.get();
        if(next==null || cells==null || !next.current(now) || !cells.owns(next) || next.count()>ReceiverPlantPacket.MAXIMUM_TRIANGLES)
            throw new IllegalArgumentException("Stale or mismatched plant publication");
        if(attributes!=null && !attributes.owns(next))
            throw new IllegalArgumentException("Plant material belongs to another geometry packet");
        float[][] payload=attributes==null
                ?new float[][]{cells.headers(now),cells.indices(now),next.triangles()}
                :new float[][]{cells.headers(now),cells.indices(now),next.triangles(),attributes.attributes(now)};
        int[] pending=new int[payload.length];
        try {
            for(int index=0;index<pending.length;index++) {
                requireCurrent(next);
                int width=index==3?6:index==2?4:256;
                int height=payload[index].length/(width*4);
                float[] values=payload[index];
                if(index>=2) {
                    var layout=ReceiverPlantPacket.texturePayload(width,values);
                    width=layout.width();height=layout.height();values=layout.values();
                }
                int texture=upload.create(width,height,values);
                if(texture<=0)throw new IllegalStateException("Plant texture allocation failed");
                for(int active:textures)if(active==texture)throw new IllegalStateException("Reused active plant texture");
                for(int prior=0;prior<index;prior++)if(pending[prior]==texture)
                    throw new IllegalStateException("Reused pending plant texture");
                pending[index]=texture;
                requireCurrent(next);
            }
        } catch(RuntimeException error) {
            for(int texture:pending)if(texture!=0)upload.delete(texture);
            throw error;
        }
        int[] previous=textures;textures=pending;packet=next;publication=cells;material=attributes;
        for(int texture:previous)if(texture!=0)upload.delete(texture);
    }
    private void requireCurrent(ReceiverPlantPacket next) {
        if(!next.current(epoch.get()))throw new IllegalStateException("Plant upload owner expired");
    }
    public boolean ready() { return packet!=null && packet.current(epoch.get()); }
    public int texture(int index) {
        if(index<0 || index>=3)throw new IllegalArgumentException("Unknown plant texture");
        return ready()?textures[index]:0;
    }
    public ReceiverPlantPacket packet() { return ready()?packet:null; }
    public ReceiverPlantCellPublication publication() { return ready()?publication:null; }
    public int materialTexture() { return ready() && material!=null?textures[3]:0; }
    public ReceiverPlantMaterialPacket material() { return ready()?material:null; }
    public void invalidate() { packet=null;publication=null;material=null; }
    public void close() {
        invalidate();int[] previous=textures;textures=new int[3];
        for(int texture:previous)if(texture!=0)upload.delete(texture);
    }
}
