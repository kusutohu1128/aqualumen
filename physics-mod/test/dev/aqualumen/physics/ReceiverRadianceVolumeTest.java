package dev.aqualumen.physics;

public final class ReceiverRadianceVolumeTest {
    public static void main(String[] args) {
        Object world = new Object();
        var epoch = new ReceiverRadianceVolume.Epoch(world, 10, 2);
        check(epoch.matches(world,10,2),"Allocation-free matching epoch");
        check(!epoch.matches(null,10,2) && !epoch.matches(new Object(),10,2)
                && !epoch.matches(world,11,2) && !epoch.matches(world,10,3)
                && !epoch.matches(world,-1,2) && !epoch.matches(world,10,-1),
                "Allocation-free stale/null epoch rejection");
        var bounds = new ReceiverField.Bounds(-2, -3, -4, 2, 2, 2);
        float[] cells = new float[32], source = new float[32], sun = new float[32], faces = new float[32];
        for (int offset = 0; offset < 32; offset += 4) cells[offset] = 2;
        cells[0] = 3; source[0] = .75f; source[3] = 1;
        sun[0] = .25f; sun[3] = 1; faces[1] = 1; faces[3] = 1;
        var volume = new ReceiverRadianceVolume(epoch, bounds, cells, source, sun, faces);
        check(volume.pixel(1, 1, 1) == 7 && volume.pixel(0, 1, 0) == 4, "Shader sliced layout");
        check(volume.current(new ReceiverRadianceVolume.Epoch(world, 10, 2)), "Matching epoch");
        check(!volume.current(new ReceiverRadianceVolume.Epoch(new Object(), 10, 2)) &&
              !volume.current(new ReceiverRadianceVolume.Epoch(world, 11, 2)) &&
              !volume.current(new ReceiverRadianceVolume.Epoch(world, 10, 3)), "Stale epoch rejection");
        source[0] = 99; check(volume.source()[0] == .75f, "Owned source copy");
        float[] returned = volume.source(); returned[0] = 88;
        check(volume.source()[0] == .75f, "Returned source copy");
        source[0] = .75f;
        sun[0] = 1; rejects(() -> new ReceiverRadianceVolume(epoch, bounds, cells, source, sun, faces)); sun[0] = .25f;
        sun[3] = 0; rejects(() -> new ReceiverRadianceVolume(epoch, bounds, cells, source, sun, faces)); sun[3] = 1;
        faces[0] = 1; rejects(() -> new ReceiverRadianceVolume(epoch, bounds, cells, source, sun, faces)); faces[0] = 0;
        cells[0] = 2; rejects(() -> new ReceiverRadianceVolume(epoch, bounds, cells, source, sun, faces)); cells[0] = 3;
        source[0] = Float.NaN; rejects(() -> new ReceiverRadianceVolume(epoch, bounds, cells, source, sun, faces)); source[0] = .75f;
        rejects(() -> volume.pixel(2, 0, 0));
        rejects(() -> new ReceiverRadianceVolume(epoch, bounds, new float[4], source, sun, faces));
        System.out.println("ReceiverRadianceVolume ownership, layout, epoch and paired readiness tests passed");
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void rejects(Runnable action) {
        try { action.run(); }
        catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("Expected rejected receiver input");
    }
}
