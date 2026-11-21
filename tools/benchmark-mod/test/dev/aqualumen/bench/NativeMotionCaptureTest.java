package dev.aqualumen.bench;

import java.nio.file.Files;
import java.nio.file.Path;

public final class NativeMotionCaptureTest {
    public static void main(String[] args) throws Exception {
        Path root = Files.createTempDirectory("aqualumen-native-motion-");
        ScreenshotCompletion[] callback = new ScreenshotCompletion[1];
        Path[] destination = new Path[1];
        NativeMotionCapture capture = new NativeMotionCapture(root.resolve("sequence"), (path, completion) -> {
            destination[0] = path;
            callback[0] = completion;
        });
        require(capture.request(0, 0, -45, -65), "first request");
        Files.write(destination[0], new byte[] {1});
        require(!capture.poll(1), "partial file cannot authorize completion");
        require(!capture.request(100_000_000, 100_000_000, -44, -65), "one pending writer");
        callback[0].callback("screenshot.success");
        require(capture.poll(100_000_001), "completed callback");
        require(Files.readString(root.resolve("sequence/frames.csv")).contains("0,0,-45.000000000,-65.000000000"), "actual metadata");
        require(!capture.request(99_999_999, 99_999_999, 0, 0), "rate bound");
        require(capture.request(200_000_000, 200_000_000, -43, -65), "next request");
        callback[0].callback("screenshot.failure");
        expectFailure(() -> capture.poll(200_000_001));
        expectFailure(() -> new NativeMotionCapture(root.resolve("sequence"), (path, completion) -> {}));
        NativeMotionCapture timeout = new NativeMotionCapture(root.resolve("timeout"), (path, completion) -> {});
        require(timeout.request(0, 0, 0, 0), "timeout request");
        expectFailure(() -> timeout.poll(15_000_000_001L));
        NativeMotionCapture bounded = new NativeMotionCapture(root.resolve("bounded"), (path, completion) -> {
            Files.write(path, new byte[] {1});
            completion.callback("screenshot.success");
        });
        for (int frame = 0; frame < 80; frame++) {
            require(bounded.request(frame * 100_000_000L, frame * 100_000_000L, frame, -65), "bounded frame");
        }
        require(!bounded.request(8_000_000_000L, 8_000_000_000L, 80, -65), "frame limit");
        require(bounded.poll(8_000_000_001L), "drained writer");
        System.out.println("NativeMotionCaptureTest passed");
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private interface Action { void run() throws Exception; }

    private static void expectFailure(Action action) throws Exception {
        try { action.run(); }
        catch (IllegalStateException expected) { return; }
        throw new AssertionError("Expected failure");
    }
}
