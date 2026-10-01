package dev.aqualumen.bench;

/** Thread-visible writer callback gate; existence of a partially written file is irrelevant. */
final class ScreenshotCompletion {
    private volatile String result;
    void callback(String translationKey) { result = translationKey == null ? "unknown-callback" : translationKey; }
    boolean ready(long elapsedNanos) {
        String current = result;
        if (current == null) {
            if (elapsedNanos > 15_000_000_000L) throw new IllegalStateException("Screenshot writer callback timed out");
            return false;
        }
        if (!current.equals("screenshot.success")) throw new IllegalStateException("Screenshot writer callback failed: " + current);
        return true;
    }
}
