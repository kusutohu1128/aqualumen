package dev.aqualumen.bench;

/** Real production callback gate; file presence must not mean writer completion. */
public final class ScreenshotCompletionTest {
    public static void main(String[] args) {
        ScreenshotCompletion gate = new ScreenshotCompletion();
        if (gate.ready(1_000_000L)) throw new AssertionError("Pending callback must forbid copy even when a partial file already exists");
        gate.callback("screenshot.success");
        if (!gate.ready(1_000_001L)) throw new AssertionError("Successful writer callback must make copy eligible");
        ScreenshotCompletion failed = new ScreenshotCompletion();
        failed.callback("screenshot.failure");
        rejects(() -> failed.ready(1L), "Writer failure must reject an existing partial file");
        ScreenshotCompletion unknown = new ScreenshotCompletion();
        unknown.callback(null);
        rejects(() -> unknown.ready(1L), "Unknown callback must not make copy eligible");
        ScreenshotCompletion timedOut = new ScreenshotCompletion();
        rejects(() -> timedOut.ready(15_000_000_001L), "Missing callback must time out");
        ScreenshotCompletion nextCapture = new ScreenshotCompletion();
        timedOut.callback("screenshot.success");
        if (nextCapture.ready(1L)) throw new AssertionError("A stale previous-capture callback must not release the next gate");
        nextCapture.callback("screenshot.success");
        if (!nextCapture.ready(2L)) throw new AssertionError("Each capture needs its own successful callback");
        System.out.println("Screenshot callback readiness, failure, timeout and stale-token regressions passed");
    }

    private static void rejects(Runnable check, String message) {
        try { check.run(); }
        catch (IllegalStateException expected) { return; }
        throw new AssertionError(message);
    }
}
