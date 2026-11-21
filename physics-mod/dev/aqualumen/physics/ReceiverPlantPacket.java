package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;
import java.util.IdentityHashMap;

public final class ReceiverPlantPacket {
    public static final int MAXIMUM_TRIANGLES=131072;
    public record TexturePayload(int width,int height,float[] values) {
        public TexturePayload { values=values.clone(); }
        @Override public float[] values() { return values.clone(); }
    }
    public static TexturePayload texturePayload(int texelsPerPrimitive,float[] attributes) {
        if((texelsPerPrimitive!=4 && texelsPerPrimitive!=6) || attributes==null
                || attributes.length==0 || attributes.length%(texelsPerPrimitive*4)!=0)
            throw new IllegalArgumentException("Invalid plant texture payload");
        int count=attributes.length/(texelsPerPrimitive*4);
        if(count>131072)throw new IllegalArgumentException("Plant tiled payload exceeds capacity");
        for(float value:attributes)if(!Float.isFinite(value))
            throw new IllegalArgumentException("Nonfinite plant tiled payload");
        if(count<=16384)return new TexturePayload(texelsPerPrimitive,count,attributes);
        int width=texelsPerPrimitive*64,height=(count+63)/64;
        return new TexturePayload(width,height,java.util.Arrays.copyOf(attributes,width*height*4));
    }
    private final ReceiverRadianceVolume.Epoch epoch;
    private final double x, y, z;
    private final float[] triangles;
    private final List<ReceiverPlantPacket> members;
    private ReceiverPlantPacket(ReceiverRadianceVolume.Epoch epoch, double x, double y, double z, float[] triangles) {
        this(epoch,x,y,z,triangles,List.of());
    }
    private ReceiverPlantPacket(ReceiverRadianceVolume.Epoch epoch, double x, double y, double z,
            float[] triangles,List<ReceiverPlantPacket> members) {
        this.epoch = epoch; this.x = x; this.y = y; this.z = z; this.triangles = triangles.clone();
        this.members=List.copyOf(members);
    }
    public static ReceiverPlantPacket capture(ReceiverRadianceVolume.Epoch epoch,
            List<ReceiverQuadIntersection.Quad> quads, double x, double y, double z, boolean alphaQualified) {
        Objects.requireNonNull(epoch);
        var owned = List.copyOf(quads);
        if (owned.isEmpty() || owned.size() > 256 || !Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z))
            throw new IllegalArgumentException("Unbounded plant packet");
        float[] triangles = new float[owned.size()*32];
        int offset = 0;
        for (var quad : owned) {
            for (var points : List.of(List.of(quad.first(),quad.second(),quad.third()),
                    List.of(quad.first(),quad.third(),quad.fourth()))) {
                for (int index = 0; index < 3; index++) {
                    var point = points.get(index);
                    triangles[offset+index*4] = relative(point.x(),x);
                    triangles[offset+index*4+1] = relative(point.y(),y);
                    triangles[offset+index*4+2] = relative(point.z(),z);
                    if (point.u() < 0 || point.u() > 1 || point.v() < 0 || point.v() > 1)
                        throw new IllegalArgumentException("Unsupported plant atlas UV");
                    triangles[offset+index*4+3] = (float)point.u();
                    triangles[offset+12+index] = (float)point.v();
                }
                triangles[offset+15] = alphaQualified ? 1 : 0;
                offset += 16;
            }
        }
        return new ReceiverPlantPacket(epoch,x,y,z,triangles);
    }
    private static float relative(double position, double origin) {
        double local = position-origin;
        if (!Double.isFinite(local) || Math.abs(local) > 128)
            throw new IllegalArgumentException("Plant position exceeds packet coordinate domain");
        return (float)local;
    }
    public boolean current(ReceiverRadianceVolume.Epoch now) {
        return now != null && epoch.world() == now.world() && epoch.frame() == now.frame() && epoch.resources() == now.resources();
    }
    public int count() { return triangles.length/16; }
    public record Bounds(double minX,double minY,double minZ,double maxX,double maxY,double maxZ) {}
    public Bounds bounds(ReceiverRadianceVolume.Epoch now) {
        if(!current(now))throw new IllegalStateException("Stale plant bounds input");
        double minX=Double.POSITIVE_INFINITY,minY=minX,minZ=minX;
        double maxX=Double.NEGATIVE_INFINITY,maxY=maxX,maxZ=maxX;
        for(int primitive=0;primitive<count();primitive++)
            for(int vertex=0;vertex<3;vertex++) {
                int offset=primitive*16+vertex*4;
                double worldX=x+triangles[offset],worldY=y+triangles[offset+1],worldZ=z+triangles[offset+2];
                minX=Math.min(minX,worldX);minY=Math.min(minY,worldY);minZ=Math.min(minZ,worldZ);
                maxX=Math.max(maxX,worldX);maxY=Math.max(maxY,worldY);maxZ=Math.max(maxZ,worldZ);
            }
        return new Bounds(minX,minY,minZ,maxX,maxY,maxZ);
    }
    public static ReceiverPlantPacket aggregate(ReceiverRadianceVolume.Epoch epoch,
            List<ReceiverPlantPacket> packets, int maximumTriangles) {
        Objects.requireNonNull(epoch);
        var owned = List.copyOf(packets);
        if (owned.isEmpty() || maximumTriangles < 1 || maximumTriangles > MAXIMUM_TRIANGLES)
            throw new IllegalArgumentException("Unbounded plant aggregation");
        var reference = owned.getFirst();
        var seen = new IdentityHashMap<ReceiverPlantPacket,Boolean>();
        int count = 0;
        for (var packet : owned) {
            if (!packet.current(epoch)) throw new IllegalStateException("Stale plant aggregation input");
            if (packet.x != reference.x || packet.y != reference.y || packet.z != reference.z)
                throw new IllegalArgumentException("Plant aggregation requires one coordinate reference");
            if (seen.put(packet,Boolean.TRUE) != null || packet.count() > maximumTriangles-count)
                throw new IllegalArgumentException("Duplicate or overflowing plant aggregation");
            count += packet.count();
        }
        float[] triangles = new float[count*16];
        int offset = 0;
        for (var packet : owned) {
            System.arraycopy(packet.triangles,0,triangles,offset,packet.triangles.length);
            offset += packet.triangles.length;
        }
        return new ReceiverPlantPacket(epoch,reference.x,reference.y,reference.z,triangles,owned);
    }
    public boolean aggregationMatches(List<ReceiverPlantPacket> candidates) {
        if(members.isEmpty() || candidates.size()!=members.size())return false;
        for(int index=0;index<members.size();index++)if(members.get(index)!=candidates.get(index))return false;
        return true;
    }
    public ReceiverPlantPacket select(int[] indices) {
        Objects.requireNonNull(indices);
        if (indices.length < 1 || indices.length > count()) throw new IllegalArgumentException("Invalid plant selection extent");
        boolean[] seen = new boolean[count()]; float[] selected = new float[indices.length*16];
        for (int index = 0; index < indices.length; index++) {
            int primitive = indices[index];
            if (primitive < 0 || primitive >= count() || seen[primitive])
                throw new IllegalArgumentException("Invalid or duplicate plant primitive");
            seen[primitive] = true;
            System.arraycopy(triangles,primitive*16,selected,index*16,16);
        }
        return new ReceiverPlantPacket(epoch,x,y,z,selected);
    }
    public float[] triangles() { return triangles.clone(); }
    public double x() { return x; }
    public double y() { return y; }
    public double z() { return z; }
}
