package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;

public final class ReceiverPlantCellPublication {
    public record Proof(List<ReceiverWaterVolume.Observation> waterColumn, boolean completeModelOwners) {
        public Proof { waterColumn = List.copyOf(waterColumn); }
    }
    public interface World {
        ReceiverRadianceVolume.Epoch epoch();
        Proof proof(int x, int y, int z);
        void beginValidation();
    }
    private final ReceiverRadianceVolume.Epoch epoch;
    private final ReceiverPlantCellIndex.Window window;
    private final float[] headers, indices;
    private final int memberships;
    private final ReceiverPlantCellIndex index;
    private ReceiverPlantCellPublication(ReceiverRadianceVolume.Epoch epoch, ReceiverPlantCellIndex.Window window,
            float[] headers, float[] indices, int memberships, ReceiverPlantCellIndex index) {
        this.epoch = epoch; this.window = window; this.headers = headers; this.indices = indices; this.memberships = memberships;
        this.index = index;
    }
    public static ReceiverPlantCellPublication capture(ReceiverPlantCellIndex index, ReceiverRadianceVolume.Epoch epoch, World world) {
        Objects.requireNonNull(index); Objects.requireNonNull(epoch); Objects.requireNonNull(world);
        requireCurrent(epoch,world.epoch());
        var window = index.window();
        int[] offsets = index.offsets(epoch), primitives = index.primitives(epoch);
        int cells = window.width()*window.height()*window.depth();
        float[] headers = new float[256*((cells+2+255)/256)*4];
        float[] indices = new float[256*Math.max(1,(primitives.length+255)/256)*4];
        Proof[] witnesses = new Proof[cells];
        for (int cell = 0; cell < cells; cell++) {
            int x = cell%window.width(), row = cell/window.width(), z = row%window.depth(), y = row/window.depth();
            Proof proof = world.proof(window.x()+x,window.y()+y,window.z()+z);
            witnesses[cell] = proof;
            int count = offsets[cell+1]-offsets[cell];
            if (count > 512) throw new IllegalArgumentException("Plant cell primitive capacity exceeded");
            headers[cell*4] = offsets[cell]; headers[cell*4+1] = count;
            headers[cell*4+2] = proof != null && ReceiverWaterVolume.fullColumn(proof.waterColumn()) ? 1 : 0;
            headers[cell*4+3] = proof != null && proof.completeModelOwners() ? 1 : 0;
        }
        for (int membership = 0; membership < primitives.length; membership++) indices[membership*4] = primitives[membership];
        headers[cells*4] = window.width(); headers[cells*4+1] = window.height(); headers[cells*4+2] = window.depth();
        headers[cells*4+3] = primitives.length; headers[(cells+1)*4] = index.primitiveCount();
        world.beginValidation();
        for (int cell = 0; cell < cells; cell++) {
            int x = cell%window.width(), row = cell/window.width(), z = row%window.depth(), y = row/window.depth();
            if (!Objects.equals(witnesses[cell],world.proof(window.x()+x,window.y()+y,window.z()+z)))
                throw new IllegalStateException("Plant fluid/model proof changed before publication");
        }
        requireCurrent(epoch,world.epoch());
        return new ReceiverPlantCellPublication(epoch,window,headers,indices,primitives.length,index);
    }
    private static void requireCurrent(ReceiverRadianceVolume.Epoch expected, ReceiverRadianceVolume.Epoch actual) {
        if (actual == null || expected.world() != actual.world() || expected.frame() != actual.frame() || expected.resources() != actual.resources())
            throw new IllegalStateException("Plant cell publication owner expired");
    }
    public float[] headers(ReceiverRadianceVolume.Epoch now) { requireCurrent(epoch,now); return headers.clone(); }
    public float[] indices(ReceiverRadianceVolume.Epoch now) { requireCurrent(epoch,now); return indices.clone(); }
    public int memberships() { return memberships; }
    public boolean owns(ReceiverPlantPacket packet) { return index.owns(packet); }
    public ReceiverPlantCellIndex.Window window() { return window; }
}
