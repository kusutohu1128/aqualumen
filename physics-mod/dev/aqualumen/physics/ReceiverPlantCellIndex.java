package dev.aqualumen.physics;

import java.util.Arrays;
import java.util.Objects;

public final class ReceiverPlantCellIndex {
    public record Window(int x, int y, int z, int width, int height, int depth) {
        public Window {
            if (width < 1 || width > 96 || height < 1 || height > 64 || depth < 1 || depth > 96
                    || (long)x+width > Integer.MAX_VALUE || (long)y+height > Integer.MAX_VALUE || (long)z+depth > Integer.MAX_VALUE)
                throw new IllegalArgumentException("Unbounded plant index window");
        }
        public Window expanded(int halo,int minimumY,int maximumY) {
            if(halo<0 || halo>2 || minimumY>=maximumY || y<minimumY || (long)y+height>maximumY
                    || (long)x-halo<Integer.MIN_VALUE || (long)z-halo<Integer.MIN_VALUE)
                throw new IllegalArgumentException("Unbounded plant owner halo");
            int bottom=(int)Math.max(minimumY,(long)y-halo);
            int ceiling=(int)Math.min(maximumY,(long)y+height+halo);
            return new Window(x-halo,bottom,z-halo,width+halo*2,ceiling-bottom,depth+halo*2);
        }
    }
    private record Range(int minX, int minY, int minZ, int maxX, int maxY, int maxZ) {}
    private final ReceiverPlantPacket packet;
    private final Window window;
    private final int[] offsets, primitives;

    private ReceiverPlantCellIndex(ReceiverPlantPacket packet, Window window, int[] offsets, int[] primitives) {
        this.packet = packet; this.window = window; this.offsets = offsets; this.primitives = primitives;
    }
    public static ReceiverPlantCellIndex capture(ReceiverPlantPacket packet, Window window,
            ReceiverRadianceVolume.Epoch epoch, int maximumMemberships) {
        Objects.requireNonNull(packet); Objects.requireNonNull(window);
        if (!packet.current(epoch)) throw new IllegalStateException("Stale plant index input");
        if (maximumMemberships < 1 || maximumMemberships > 1048576)
            throw new IllegalArgumentException("Unbounded plant memberships");
        int cells = window.width()*window.height()*window.depth();
        int[] counts = new int[cells];
        float[] values = packet.triangles(); Range[] ranges = new Range[packet.count()];
        int memberships = 0;
        for (int primitive = 0; primitive < packet.count(); primitive++) {
            int offset = primitive*16;
            double minX = Double.POSITIVE_INFINITY, minY = minX, minZ = minX;
            double maxX = Double.NEGATIVE_INFINITY, maxY = maxX, maxZ = maxX;
            for (int vertex = 0; vertex < 3; vertex++) {
                double x = packet.x()+values[offset+vertex*4], y = packet.y()+values[offset+vertex*4+1], z = packet.z()+values[offset+vertex*4+2];
                minX = Math.min(minX,x); minY = Math.min(minY,y); minZ = Math.min(minZ,z);
                maxX = Math.max(maxX,x); maxY = Math.max(maxY,y); maxZ = Math.max(maxZ,z);
            }
            var range = new Range(lower(minX),lower(minY),lower(minZ),upper(maxX),upper(maxY),upper(maxZ));
            if (range.minX() < window.x() || range.minY() < window.y() || range.minZ() < window.z()
                    || (long)range.maxX() >= (long)window.x()+window.width()
                    || (long)range.maxY() >= (long)window.y()+window.height()
                    || (long)range.maxZ() >= (long)window.z()+window.depth())
                throw new IllegalArgumentException("Plant index would truncate geometry or boundary contacts");
            long extent = ((long)range.maxX()-range.minX()+1)*((long)range.maxY()-range.minY()+1)*((long)range.maxZ()-range.minZ()+1);
            if (extent > maximumMemberships-memberships) throw new IllegalArgumentException("Plant index membership capacity exceeded");
            memberships += (int)extent; ranges[primitive] = range;
            for (int y = range.minY(); y <= range.maxY(); y++)
                for (int z = range.minZ(); z <= range.maxZ(); z++)
                    for (int x = range.minX(); x <= range.maxX(); x++) counts[index(window,x,y,z)]++;
        }
        int[] offsets = new int[cells+1];
        for (int cell = 0; cell < cells; cell++) offsets[cell+1] = offsets[cell]+counts[cell];
        int[] cursors = offsets.clone(), primitives = new int[memberships];
        for (int primitive = 0; primitive < ranges.length; primitive++) {
            var range = ranges[primitive];
            for (int y = range.minY(); y <= range.maxY(); y++)
                for (int z = range.minZ(); z <= range.maxZ(); z++)
                    for (int x = range.minX(); x <= range.maxX(); x++) primitives[cursors[index(window,x,y,z)]++] = primitive;
        }
        return new ReceiverPlantCellIndex(packet,window,offsets,primitives);
    }
    private static int lower(double coordinate) { return voxel(Math.nextDown(coordinate)); }
    private static int upper(double coordinate) { return voxel(Math.nextUp(coordinate)); }
    private static int voxel(double coordinate) {
        double value = Math.floor(coordinate);
        if (!Double.isFinite(value) || value < Integer.MIN_VALUE || value > Integer.MAX_VALUE)
            throw new IllegalArgumentException("Plant voxel exceeds coordinate domain");
        return (int)value;
    }
    private static int index(Window window, int x, int y, int z) {
        return ((y-window.y())*window.depth()+z-window.z())*window.width()+x-window.x();
    }
    public int[] candidates(int x, int y, int z, ReceiverRadianceVolume.Epoch now) {
        if (!packet.current(now)) throw new IllegalStateException("Plant index epoch expired");
        long localX = (long)x-window.x(), localY = (long)y-window.y(), localZ = (long)z-window.z();
        if (localX < 0 || localY < 0 || localZ < 0 || localX >= window.width() || localY >= window.height() || localZ >= window.depth())
            throw new IllegalArgumentException("Plant lookup outside validated window");
        int cell = index(window,x,y,z);
        return Arrays.copyOfRange(primitives,offsets[cell],offsets[cell+1]);
    }
    public int memberships() { return primitives.length; }
    public int primitiveCount() { return packet.count(); }
    public boolean owns(ReceiverPlantPacket candidate) { return packet==candidate; }
    public Window window() { return window; }
    int[] offsets(ReceiverRadianceVolume.Epoch now) {
        if (!packet.current(now)) throw new IllegalStateException("Plant index epoch expired");
        return offsets.clone();
    }
    int[] primitives(ReceiverRadianceVolume.Epoch now) {
        if (!packet.current(now)) throw new IllegalStateException("Plant index epoch expired");
        return primitives.clone();
    }
}
