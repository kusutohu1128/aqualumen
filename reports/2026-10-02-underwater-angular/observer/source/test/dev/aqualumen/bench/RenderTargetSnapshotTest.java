package dev.aqualumen.bench;

import java.lang.reflect.InvocationTargetException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Public observations and externally visible GL binding, not private reflection mocks. */
public final class RenderTargetSnapshotTest {
    public static void main(String[] args) {
        capturesActualStorageAndRestoresBinding();
        unallocatedStorageIsNotSuccess();
        nonexistentTextureCannotCreateAnObservation();
        queryFailureRestoresBindingAndRedactsMessages();
        missingSelectedTargetIsNotPartialSuccess();
        failedRestoreCannotClaimSuccess();
        reflectedFailureExportsOnlyUnderlyingClass();
        absentRuntimeIsUnavailableWithoutGpuCalls();
        System.out.println("Render target snapshot CPU observation and binding-restoration tests passed");
    }

    private static void absentRuntimeIsUnavailableWithoutGpuCalls() {
        // This executable intentionally has neither Iris nor LWJGL on its CPU classpath.
        Map<String, Object> result = RenderTargetSnapshot.capture();
        require(Boolean.FALSE.equals(result.get("available")) && "ClassNotFoundException".equals(result.get("errorClass")), "Missing actual runtime must be unavailable, not a fabricated storage observation");
        require(((List<?>) result.get("queries")).isEmpty() && Boolean.FALSE.equals(result.get("bindingRestored")), "Missing Iris cannot claim a GL query or restoration");
    }

    private static void reflectedFailureExportsOnlyUnderlyingClass() {
        Boundary boundary = new Boundary();
        boundary.queryError = new InvocationTargetException(new IllegalArgumentException("secret-token"));
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.FALSE.equals(result.get("available")) && "IllegalArgumentException".equals(result.get("errorClass")), "Reflection failure must name only its underlying class");
        require(boundary.binding == 77 && !result.toString().contains("secret-token"), "Reflected failure must restore binding without leaking cause message");
    }

    private static void failedRestoreCannotClaimSuccess() {
        Boundary boundary = new Boundary();
        boundary.restoreError = true;
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.FALSE.equals(result.get("available")) && Boolean.FALSE.equals(result.get("bindingRestored")), "Failed GL restore must invalidate otherwise successful observations");
        require("IllegalStateException".equals(result.get("restoreErrorClass")), "Restore failure exports class, not message");
        require(!result.toString().contains("secret-token"), "Restore failure must not leak its message");
    }

    private static void missingSelectedTargetIsNotPartialSuccess() {
        Boundary boundary = new Boundary();
        boundary.targets.remove(8);
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.FALSE.equals(result.get("available")), "Five queried targets cannot stand in for all six");
        require(boundary.binding == 77 && Boolean.TRUE.equals(result.get("bindingRestored")), "Missing final target must restore binding after earlier queries");
    }

    private static void queryFailureRestoresBindingAndRedactsMessages() {
        Boundary boundary = new Boundary();
        boundary.queryError = new IllegalStateException("secret-token /private/account-path");
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.FALSE.equals(result.get("available")), "A failed query must not export success");
        require("IllegalStateException".equals(result.get("errorClass")), "Export exception class only");
        require(!result.toString().contains("secret-token") && !result.toString().contains("account-path"), "Exception messages must not leak");
        require(boundary.binding == 77 && Boolean.TRUE.equals(result.get("bindingRestored")), "Query failure must restore original binding");
    }

    private static void nonexistentTextureCannotCreateAnObservation() {
        Boundary boundary = new Boundary();
        boundary.registeredTextures = false;
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.FALSE.equals(result.get("available")), "Nonexistent texture IDs must be rejected before a GL bind could create them");
        require(boundary.binding == 77, "Nonexistent texture rejection must leave original binding intact");
    }

    private static void unallocatedStorageIsNotSuccess() {
        Boundary boundary = new Boundary();
        boundary.storage = new RenderTargetSnapshot.TextureLevel(0, 0, 0);
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.FALSE.equals(result.get("available")), "Zero/unallocated GL storage must never count as a successful query");
        require(boundary.binding == 77, "Unavailable storage must still restore binding");
    }

    private static void capturesActualStorageAndRestoresBinding() {
        Boundary boundary = new Boundary();
        Map<String, Object> result = RenderTargetSnapshot.capture(boundary);
        require(Boolean.TRUE.equals(result.get("available")), "Existing main/alt storage must be available");
        require(Integer.valueOf(9).equals(result.get("renderTargetCount")), "Record actual Iris target count");
        List<?> queries = (List<?>) result.get("queries");
        require(queries.size() == 6, "Export all six selected targets, not unqueried success");
        Map<?, ?> target = (Map<?, ?>) queries.get(0);
        require(Integer.valueOf(0).equals(target.get("index")), "Target identity must be exported");
        require("RGBA16F".equals(target.get("declaredFormat")), "Export declared format without treating it as actual storage");
        Map<?, ?> main = (Map<?, ?>) target.get("main"), alt = (Map<?, ?>) target.get("alt");
        require(Integer.valueOf(100).equals(main.get("textureId")), "Export main texture ID");
        require(Integer.valueOf(34842).equals(main.get("actualFormat")), "Actual main storage comes from GL observation");
        require(Integer.valueOf(32856).equals(alt.get("actualFormat")), "Different alt storage must not inherit the declaration");
        require(Integer.valueOf(2560).equals(main.get("width")) && Integer.valueOf(1440).equals(main.get("height")), "Export actual dimensions");
        require(boundary.binding == 77 && Boolean.TRUE.equals(result.get("bindingRestored")), "Restore caller's current-unit texture binding");
    }

    private static final class Boundary implements RenderTargetSnapshot.SystemBoundary {
        final Map<Integer, RenderTargetSnapshot.Target> targets = new LinkedHashMap<>();
        int binding = 77;
        RenderTargetSnapshot.TextureLevel storage;
        boolean registeredTextures = true;
        Exception queryError;
        boolean restoreError;
        Boundary() {
            for (int index : new int[]{0, 4, 5, 6, 7, 8})
                targets.put(index, new RenderTargetSnapshot.Target("RGBA16F", 100 + index, 200 + index, 2560, 1440));
        }
        public RenderTargetSnapshot.Inventory existingTargets() { return new RenderTargetSnapshot.Inventory(9, targets); }
        public int textureBinding2D() { return binding; }
        public boolean textureExists(int texture) { return registeredTextures; }
        public void bindTexture2D(int texture) {
            if (restoreError && texture == 77) throw new IllegalStateException("secret-token");
            binding = texture;
        }
        public RenderTargetSnapshot.TextureLevel textureLevel() throws Exception {
            if (queryError != null) throw queryError;
            return storage == null ? new RenderTargetSnapshot.TextureLevel(binding < 200 ? 34842 : 32856, 2560, 1440) : storage;
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
