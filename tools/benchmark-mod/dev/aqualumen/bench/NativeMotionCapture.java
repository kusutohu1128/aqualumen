package dev.aqualumen.bench;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Locale;

final class NativeMotionCapture {
    interface Writer {
        void capture(Path destination, ScreenshotCompletion completion) throws Exception;
    }

    private final Path directory;
    private final Writer writer;
    private long previousRequest = Long.MIN_VALUE;
    private int frames;
    private Path pendingPath;
    private ScreenshotCompletion pendingCompletion;
    private long pendingStarted;
    private String pendingRow;

    NativeMotionCapture(Path directory, Writer writer) throws Exception {
        if (Files.exists(directory) || Files.isSymbolicLink(directory)) {
            throw new IllegalStateException("Motion directory already exists");
        }
        Files.createDirectory(directory);
        this.directory = directory;
        this.writer = writer;
        Files.writeString(directory.resolve("frames.csv"), "frame,elapsed_ns,yaw,pitch\n", StandardOpenOption.CREATE_NEW);
    }

    boolean poll(long now) throws Exception {
        if (pendingCompletion == null) return true;
        if (!pendingCompletion.ready(now - pendingStarted)) return false;
        if (!Files.isRegularFile(pendingPath) || Files.isSymbolicLink(pendingPath) || Files.size(pendingPath) == 0) {
            throw new IllegalStateException("Completed motion frame is missing or empty");
        }
        Files.writeString(directory.resolve("frames.csv"), pendingRow, StandardOpenOption.APPEND);
        frames++;
        pendingCompletion = null;
        pendingPath = null;
        return true;
    }

    boolean request(long now, long elapsed, double yaw, double pitch) throws Exception {
        if (elapsed < 0 || !Double.isFinite(yaw) || !Double.isFinite(pitch)) {
            throw new IllegalArgumentException("Invalid motion sample");
        }
        if (!poll(now) || frames >= 80) return false;
        if (previousRequest != Long.MIN_VALUE && now - previousRequest < 100_000_000L) return false;
        Path destination = directory.resolve(String.format(Locale.ROOT, "frame-%03d.png", frames));
        if (Files.exists(destination) || Files.isSymbolicLink(destination)) {
            throw new IllegalStateException("Motion frame already exists");
        }
        pendingPath = destination;
        pendingStarted = now;
        previousRequest = now;
        pendingRow = String.format(Locale.ROOT, "%d,%d,%.9f,%.9f%n", frames, elapsed, yaw, pitch);
        pendingCompletion = new ScreenshotCompletion();
        writer.capture(destination, pendingCompletion);
        return true;
    }
}
