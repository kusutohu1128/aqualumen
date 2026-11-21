package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;

public final class ReceiverPlantMaterialPacket {
    private final ReceiverPlantPacket geometry;
    private final float[] attributes;
    private ReceiverPlantMaterialPacket(ReceiverPlantPacket geometry,float[] attributes) {
        this.geometry=geometry;this.attributes=attributes;
    }
    public static ReceiverPlantMaterialPacket capture(ReceiverPlantPacket geometry,
            List<ReceiverMaterialTriangle> materials,ReceiverRadianceVolume.Epoch epoch) {
        Objects.requireNonNull(geometry);var owned=List.copyOf(materials);
        if(!geometry.current(epoch) || geometry.count()>ReceiverPlantPacket.MAXIMUM_TRIANGLES || owned.size()!=geometry.count())
            throw new IllegalArgumentException("Stale or mismatched plant material extent");
        float[] primitives=geometry.triangles(),attributes=new float[geometry.count()*24];
        for(int primitive=0;primitive<owned.size();primitive++)for(int corner=0;corner<3;corner++) {
            var point=owned.get(primitive).sample(corner==0?1:0,corner==1?1:0,corner==2?1:0,false);
            int offset=primitive*16+corner*4;
            var value=point.attributes();
            if(!point.epoch().matches(epoch.world(),epoch.frame(),epoch.resources())
                    || (float)(point.x()-geometry.x())!=primitives[offset]
                    || (float)(point.y()-geometry.y())!=primitives[offset+1]
                    || (float)(point.z()-geometry.z())!=primitives[offset+2]
                    || value.u()!=primitives[offset+3] || value.v()!=primitives[primitive*16+12+corner])
                throw new IllegalArgumentException("Plant material does not own corresponding geometry/UV");
            int destination=primitive*24+corner*8;
            float[] channels={value.u(),value.v(),value.block(),value.sky(),value.red(),value.green(),value.blue(),value.ao()};
            System.arraycopy(channels,0,attributes,destination,8);
        }
        return new ReceiverPlantMaterialPacket(geometry,attributes);
    }
    public boolean owns(ReceiverPlantPacket candidate) {return geometry==candidate;}
    public static ReceiverPlantMaterialPacket aggregate(ReceiverPlantPacket geometry,
            List<ReceiverPlantMaterialPacket> packets,ReceiverRadianceVolume.Epoch epoch) {
        Objects.requireNonNull(geometry);var owned=List.copyOf(packets);
        if(!geometry.current(epoch) || !geometry.aggregationMatches(owned.stream().map(packet->packet.geometry).toList()))
            throw new IllegalArgumentException("Stale or foreign aggregate plant material geometry");
        var expected=ReceiverPlantPacket.aggregate(epoch,owned.stream().map(packet->packet.geometry).toList(),ReceiverPlantPacket.MAXIMUM_TRIANGLES);
        if(geometry.x()!=expected.x() || geometry.y()!=expected.y() || geometry.z()!=expected.z()
                || !java.util.Arrays.equals(geometry.triangles(),expected.triangles()))
            throw new IllegalArgumentException("Aggregate material primitive order differs from geometry");
        float[] attributes=new float[geometry.count()*24];int offset=0;
        for(var packet:owned) {
            float[] values=packet.attributes(epoch);
            System.arraycopy(values,0,attributes,offset,values.length);offset+=values.length;
        }
        return new ReceiverPlantMaterialPacket(geometry,attributes);
    }
    public int count() {return geometry.count();}
    public float[] attributes(ReceiverRadianceVolume.Epoch epoch) {
        if(!geometry.current(epoch))throw new IllegalStateException("Plant material epoch expired");
        return attributes.clone();
    }
}
