package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;

public final class ReceiverSodiumScope implements AutoCloseable {
    public record GeometryFace(String face, float offsetX, float offsetY, float offsetZ,
                               List<ReceiverVertex.Input> raw, ReceiverVertex.Quad encoded,
                               List<ReceiverVertexShader.Encoded> packed, int stride) {
        public GeometryFace {
            Objects.requireNonNull(face); Objects.requireNonNull(encoded);
            raw = List.copyOf(raw);
            packed = List.copyOf(packed);
            if (raw.size() != 4 || !Float.isFinite(offsetX) || !Float.isFinite(offsetY) || !Float.isFinite(offsetZ))
                throw new IllegalArgumentException("Incomplete receiver geometry");
            if (packed.isEmpty() ? stride != 0 : packed.size() != 4 || stride < 20 || stride > 128 || stride % 4 != 0)
                throw new IllegalArgumentException("Incomplete packed model face");
        }
    }
    public record GeometrySnapshot(ReceiverRadianceVolume.Epoch epoch, int x, int y, int z,
                                   String state, List<GeometryFace> faces) {
        public GeometrySnapshot {
            Objects.requireNonNull(epoch); Objects.requireNonNull(state);
            faces = List.copyOf(faces);
            if (faces.isEmpty() || faces.size() > 256) throw new IllegalArgumentException("Unbounded receiver geometry");
            if (faces.stream().anyMatch(face -> face.packed().size() != 4))
                throw new IllegalArgumentException("Unencoded model geometry");
        }
    }
    public record Snapshot(ReceiverRadianceVolume.Epoch epoch, int x, int y, int z, String state,
                           List<ReceiverVertex.Input> raw, ReceiverVertex.Quad encoded,
                           List<ReceiverVertexShader.Encoded> packed, int stride) {
        public Snapshot {
            Objects.requireNonNull(epoch); Objects.requireNonNull(state); Objects.requireNonNull(encoded);
            raw = List.copyOf(raw);
            packed = List.copyOf(packed);
            if (raw.size() != 4 || encoded.size() != 4) throw new IllegalArgumentException("Incomplete receiver face");
            if (packed.isEmpty() ? stride != 0 : packed.size() != 4 || stride < 20 || stride > 128 || stride % 4 != 0)
                throw new IllegalArgumentException("Incomplete packed receiver face");
        }
    }
    private static final ThreadLocal<ReceiverSodiumScope> active = new ThreadLocal<>();
    private final Thread owner = Thread.currentThread();
    private final ReceiverRadianceVolume.Epoch epoch;
    private final Object renderer;
    private final int x, y, z;
    private final String state;
    private boolean geometryMode;
    private final java.util.ArrayList<GeometryFace> geometryFaces = new java.util.ArrayList<>();
    private Snapshot snapshot;
    private boolean invalid, closed;
    private int faces;
    private boolean encodingPending;
    private String diagnostic = "no full top face";

    private ReceiverSodiumScope(ReceiverRadianceVolume.Epoch epoch, Object renderer, int x, int y, int z, String state) {
        this.epoch = Objects.requireNonNull(epoch); this.renderer = Objects.requireNonNull(renderer);
        this.x = x; this.y = y; this.z = z; this.state = Objects.requireNonNull(state);
    }

    public static ReceiverSodiumScope open(ReceiverRadianceVolume.Epoch epoch, Object renderer, int x, int y, int z, String state) {
        if (active.get() != null) throw new IllegalStateException("Nested receiver meshing unsupported");
        var scope = new ReceiverSodiumScope(epoch, renderer, x, y, z, state);
        active.set(scope); return scope;
    }

    public static ReceiverSodiumScope openGeometry(ReceiverRadianceVolume.Epoch epoch, Object renderer,
                                                  int x, int y, int z, String state) {
        var scope = open(epoch,renderer,x,y,z,state);
        scope.geometryMode = true;
        return scope;
    }

    static ReceiverSodiumScope forRenderer(Object renderer) {
        var scope = active.get();
        return scope != null && !scope.closed && scope.renderer == renderer ? scope : null;
    }

    static ReceiverSodiumScope current() { return active.get(); }
    boolean wantsEncoding() { owner(); return encodingPending && !invalid; }

    void encoded(int stride, List<ReceiverVertexShader.Encoded> packed) {
        owner();
        if (!wantsEncoding() || stride < 20 || stride > 128 || stride % 4 != 0 || packed.size() != 4) {
            reject("Invalid owned encoder extent"); return;
        }
        encodingPending = false;
        GeometryFace geometryFace = geometryMode ? geometryFaces.get(geometryFaces.size()-1) : null;
        for (int index = 0; index < 4; index++) {
            var prepared = (geometryMode ? geometryFace.encoded() : snapshot.encoded()).vertex(index);
            var actual = packed.get(index);
            if (actual.colorABGR() != prepared.colorABGR() || (actual.lightAndData() & 65535) !=
                    (prepared.blockByte() | prepared.skyByte() << 8)) {
                reject("Owned encoder color/light differs from captured face"); return;
            }
        }
        if (geometryMode)
            geometryFaces.set(geometryFaces.size()-1,new GeometryFace(geometryFace.face(),geometryFace.offsetX(),
                    geometryFace.offsetY(),geometryFace.offsetZ(),geometryFace.raw(),geometryFace.encoded(),packed,stride));
        else snapshot = new Snapshot(epoch,x,y,z,state,snapshot.raw(),snapshot.encoded(),packed,stride);
    }

    void accept(Object world, int x, int y, int z, String state, String face,
                float offsetX, float offsetY, float offsetZ, ReceiverVertex.Input[] vertices, boolean separateAo) {
        owner();
        if (geometryMode && encodingPending) invalid = true;
        encodingPending = false;
        faces++;
        diagnostic = "face=" + face + " worldMatch=" + (world == epoch.world()) + " cell=" + x + "," + y + "," + z +
                " state=" + state + " offset=" + offsetX + "," + offsetY + "," + offsetZ;
        if (world != epoch.world() || this.x != x || this.y != y || this.z != z || !this.state.equals(state)) {
            invalid = true; return;
        }
        if (geometryMode) {
            var prepared = ReceiverVertex.capture(vertices,separateAo);
            if (geometryFaces.size() >= 256 || face == null || prepared == null
                    || !Float.isFinite(offsetX) || !Float.isFinite(offsetY) || !Float.isFinite(offsetZ)) {
                invalid = true; return;
            }
            geometryFaces.add(new GeometryFace(face,offsetX,offsetY,offsetZ,List.of(vertices.clone()),prepared,List.of(),0));
            encodingPending = true;
            return;
        }
        if (!"UP".equals(face)) return;
        if (snapshot != null) { invalid = true; return; }
        var encoded = ReceiverVertex.capture(vertices, separateAo);
        if (encoded == null) { invalid = true; return; }
        int mask = 0;
        int[] corners = new int[4];
        for (int index = 0; index < 4; index++) {
            var vertex = vertices[index];
            double localX = vertex.x() - offsetX, localY = vertex.y() - offsetY, localZ = vertex.z() - offsetZ;
            if (!Double.isFinite(localX) || !Double.isFinite(localY) || !Double.isFinite(localZ) || Math.abs(localY - 1) > 1e-6) {
                invalid = true; return;
            }
            int cornerX = corner(localX), cornerZ = corner(localZ);
            if (cornerX < 0 || cornerZ < 0) { invalid = true; return; }
            corners[index] = cornerX + 2 * cornerZ;
            int bit = 1 << corners[index];
            if ((mask & bit) != 0) { invalid = true; return; }
            mask |= bit;
        }
        for (int index = 0; index < 4; index++) {
            int difference = corners[index] ^ corners[(index + 1) % 4];
            if (difference != 1 && difference != 2) { invalid = true; return; }
        }
        snapshot = new Snapshot(epoch, x, y, z, state, List.of(vertices.clone()), encoded, List.of(), 0);
        encodingPending = true;
    }

    void reject(String reason) { owner(); invalid = true; diagnostic = reason; }
    public Snapshot finish() { owner(); return invalid ? null : snapshot; }
    public GeometrySnapshot finishGeometry() {
        owner();
        return !geometryMode || invalid || encodingPending || geometryFaces.isEmpty()
                || geometryFaces.stream().anyMatch(face -> face.packed().size() != 4) ? null
                : new GeometrySnapshot(epoch,x,y,z,state,geometryFaces);
    }
    public String status() { owner(); return "faces=" + faces + " invalid=" + invalid + " " + diagnostic; }
    private void owner() {
        if (closed || Thread.currentThread() != owner || active.get() != this)
            throw new IllegalStateException("Receiver mesher owner unavailable");
    }
    private static int corner(double value) { return Math.abs(value) < 1e-6 ? 0 : Math.abs(value - 1) < 1e-6 ? 1 : -1; }
    @Override public void close() { owner(); closed = true; active.remove(); }
}
