package dev.aqualumen.physics;

import java.util.Objects;

public final class ReceiverRadianceVolume {
    public record Epoch(Object world, long frame, long resources) {
        public Epoch {
            Objects.requireNonNull(world);
            if (frame < 0 || resources < 0) throw new IllegalArgumentException("Invalid receiver epoch");
        }
        public boolean matches(Object currentWorld,long currentFrame,long currentResources) {
            return world==currentWorld && frame==currentFrame && resources==currentResources;
        }
    }

    private final Epoch epoch;
    private final ReceiverField.Bounds bounds;
    private final float[] cells, source, sun, faces;

    public ReceiverRadianceVolume(Epoch epoch, ReceiverField.Bounds bounds,
                                  float[] cells, float[] source, float[] sun, float[] faces) {
        this.epoch = Objects.requireNonNull(epoch);
        this.bounds = Objects.requireNonNull(bounds);
        int length = bounds.width() * bounds.height() * bounds.depth() * 4;
        this.cells = copy(cells, length);
        this.source = copy(source, length);
        this.sun = copy(sun, length);
        this.faces = copy(faces, length);
        validateTables(this.cells,this.source,this.sun,this.faces);
    }

    static void validateTables(float[] cells,float[] source,float[] sun,float[] faces) {
        int length=cells.length;
        if(length==0 || length%4!=0 || source.length!=length || sun.length!=length || faces.length!=length)
            throw new IllegalArgumentException("Receiver table extent mismatch");
        for(float[] table:new float[][]{cells,source,sun,faces})
            for(float value:table) if(!Float.isFinite(value)) throw new IllegalArgumentException("Nonfinite receiver input");
        for (int offset = 0; offset < length; offset += 4) {
            float kind = cells[offset];
            if (kind != 0 && kind != 2 && kind != 3 && kind != 4 && kind != 5) throw new IllegalArgumentException("Unsupported receiver cell");
            if(kind==4 && (cells[offset+1]<=0 || cells[offset+1]>=2 || cells[offset+1]==1
                    || cells[offset+2]!=1 || cells[offset+3]!=1))
                throw new IllegalArgumentException("Unqualified partial-water geometry");
            if(kind==5 && (cells[offset+1]<=-1 || cells[offset+1]>=0
                    || cells[offset+2]!=1 || cells[offset+3]!=1))
                throw new IllegalArgumentException("Unqualified upper water-interface geometry");
            if (kind != 3) {
                if (source[offset + 3] != 0 || sun[offset + 3] != 0 || faces[offset + 3] != 0)
                    throw new IllegalArgumentException("Nonopaque cell cannot own surface radiance");
                continue;
            }
            if (source[offset + 3] != sun[offset + 3] || source[offset + 3] != faces[offset + 3] ||
                    (source[offset + 3] != 0 && source[offset + 3] != 1))
                throw new IllegalArgumentException("Receiver source readiness is not paired");
            if (source[offset + 3] == 0) continue;
            float normalLength = 0;
            for (int channel = 0; channel < 3; channel++) {
                if (source[offset + channel] < 0 || sun[offset + channel] < 0 ||
                        sun[offset + channel] > source[offset + channel])
                    throw new IllegalArgumentException("Invalid receiver radiance attribution");
                float normal = faces[offset + channel];
                if (normal != 0 && normal != 1 && normal != -1) throw new IllegalArgumentException("Receiver face is not axial");
                normalLength += Math.abs(normal);
            }
            if (normalLength != 1) throw new IllegalArgumentException("Receiver must own one declared face");
        }
    }

    private static float[] copy(float[] values, int length) {
        if (values == null || values.length != length) throw new IllegalArgumentException("Receiver texture extent mismatch");
        float[] owned = values.clone();
        return owned;
    }

    public boolean current(Epoch now) {
        return now != null && epoch.world() == now.world() && epoch.frame() == now.frame() && epoch.resources() == now.resources();
    }

    public int pixel(int x, int y, int z) {
        if (x < 0 || y < 0 || z < 0 || x >= bounds.width() || y >= bounds.height() || z >= bounds.depth())
            throw new IllegalArgumentException("Receiver cell outside volume");
        return x + bounds.width() * (y * bounds.depth() + z);
    }

    public ReceiverField.Bounds bounds() { return bounds; }
    public float[] cells() { return cells.clone(); }
    public float[] source() { return source.clone(); }
    public float[] sun() { return sun.clone(); }
    public float[] faces() { return faces.clone(); }
}
