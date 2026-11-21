package dev.aqualumen.physics;

import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Objects;
import java.util.UUID;

/** First-object CPU texels only. Caller owns capture coherence; no radiance or GL. */
public final class ReceiverSurface {
    private ReceiverSurface() {}
    /** Exact caller token, not proof that the caller captured matching live resources. */
    public record Stamp(UUID world, String dimension, long frame, long atlasRevision) {
        public Stamp {
            Objects.requireNonNull(world);Objects.requireNonNull(dimension);
            if(dimension.isEmpty() || frame<0 || atlasRevision<0)throw new IllegalArgumentException("Invalid capture token");
        }
    }
    public record Surface(int x, int y, int z, String blockId,
                          ReceiverFace.Face face, ReceiverTexture.Snapshot texture) {}
    public enum Status { PIXEL, GEOMETRY_ONLY, STALE }
    public record Result(Status status, ReceiverField.Result geometry,
                         ReceiverFace.Face face, ReceiverTexture.Sample pixel) {}
    private record Key(int x,int y,int z,int axis,int sign) {}
    public static final class Snapshot {
        private final ReceiverField.Snapshot geometry;
        private final Stamp stamp;
        private final Map<Key,Surface> surfaces;
        private Snapshot(ReceiverField.Snapshot geometry,Stamp stamp,Map<Key,Surface> surfaces) {
            this.geometry=geometry;this.stamp=stamp;this.surfaces=Map.copyOf(surfaces);
        }
        public Result firstSample(Stamp current, ReceiverField.Vec origin, ReceiverField.Vec direction, double metres) {
            if(!stamp.equals(current))return new Result(Status.STALE,null,null,null);
            var hit=geometry.firstHit(origin,direction,metres);
            var unready=new Result(Status.GEOMETRY_ONLY,hit,null,null);
            if(hit.status()!=ReceiverField.Status.HIT)return unready;
            double[] normal={hit.normal().x(),hit.normal().y(),hit.normal().z()};
            int axis=normal[0]!=0?0:normal[1]!=0?1:2;
            var surface=surfaces.get(new Key(hit.x(),hit.y(),hit.z(),axis,(int)normal[axis]));
            if(surface==null || surface.texture()==null || !hit.cell().blockId().equals(surface.blockId()))return unready;
            double[] local={hit.point().x()-hit.x(),hit.point().y()-hit.y(),hit.point().z()-hit.z()};
            var pixel=surface.texture().sample(surface.face(),local[(axis+1)%3],local[(axis+2)%3]);
            return pixel==null?unready:new Result(Status.PIXEL,hit,surface.face(),pixel);
        }
    }
    /** Sparse owned catalog, not a loaded-world scheduler or GPU source readiness. */
    public static Snapshot capture(ReceiverField.Snapshot geometry, Stamp stamp, List<Surface> surfaces) {
        Objects.requireNonNull(geometry);
        Objects.requireNonNull(stamp);
        Objects.requireNonNull(surfaces);
        if(surfaces.size()>4096)throw new IllegalArgumentException("Receiver face capacity exceeded");
        var copies=new HashMap<Key,Surface>();
        var textures=Collections.newSetFromMap(new IdentityHashMap<ReceiverTexture.Snapshot,Boolean>());
        long retainedTexels=0;
        for(var surface:surfaces) {
            Objects.requireNonNull(surface);Objects.requireNonNull(surface.face());Objects.requireNonNull(surface.blockId());
            if(surface.face().axis()<0 || surface.face().axis()>2 || Math.abs(surface.face().sign())!=1)
                throw new IllegalArgumentException("Invalid axis-aligned receiver face");
            if(surface.texture()!=null && textures.add(surface.texture())) {
                retainedTexels+=(long)surface.texture().width()*surface.texture().height();
                if(retainedTexels>1048576)throw new IllegalArgumentException("Receiver texture memory exceeded");
            }
            var key=new Key(surface.x(),surface.y(),surface.z(),surface.face().axis(),surface.face().sign());
            if(copies.putIfAbsent(key,surface)!=null)throw new IllegalArgumentException("Ambiguous receiver face source");
        }
        return new Snapshot(geometry,stamp,copies);
    }
}
