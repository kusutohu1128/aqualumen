package dev.aqualumen.physics;

import java.nio.file.*;
import java.util.*;

/** File-system boundary replay of an independently decoded, hash-guarded closed TEST snapshot. */
public final class ReceiverSavedReplay {
    public static void main(String[] args) throws Exception {
        var lines = Files.readAllLines(Path.of(args[0]));
        var header = lines.get(0).split("\t");
        int[] b = Arrays.stream(header).mapToInt(Integer::parseInt).toArray();
        var bounds = new ReceiverField.Bounds(b[0], b[1], b[2], b[3], b[4], b[5]);
        var cells = new HashMap<String, ReceiverField.Cell>();
        for (var line : lines.subList(1, lines.size())) {
            var p = line.split("\t");
            if (cells.put(p[0]+","+p[1]+","+p[2], new ReceiverField.Cell(ReceiverField.Kind.valueOf(p[3]), p[4])) != null)
                throw new AssertionError("Duplicate saved voxel");
        }
        if (cells.size() != bounds.width()*bounds.height()*bounds.depth()) throw new AssertionError("Incomplete saved field");
        var snapshot = ReceiverField.capture(new ReceiverField.World() {
            public boolean loaded(int x, int z) { return true; } // all bounded cells were independently decoded
            public int minY() { return -64; }
            public int maxY() { return 320; }
            public ReceiverField.Cell receiverCell(int x, int y, int z) {
                return Objects.requireNonNull(cells.get(x+","+y+","+z));
            }
        }, bounds);
        int replayed = 0;
        for (var line : Files.readAllLines(Path.of(args[1]))) {
            var p = line.split("\t");
            var origin = new ReceiverField.Vec(Double.parseDouble(p[1]), Double.parseDouble(p[2]), Double.parseDouble(p[3]));
            var ray = new ReceiverField.Vec(Double.parseDouble(p[4]), Double.parseDouble(p[5]), Double.parseDouble(p[6]));
            var hit = snapshot.firstHit(origin, ray, 48);
            if (hit.status() != ReceiverField.Status.HIT || hit.x() != Integer.parseInt(p[7])
                    || hit.y() != Integer.parseInt(p[8]) || hit.z() != Integer.parseInt(p[9])
                    || Math.abs(hit.travel() - Double.parseDouble(p[10])) > 1e-10
                    || !hit.cell().blockId().equals(p[11]) || hit.normal().x() != Double.parseDouble(p[12])
                    || hit.normal().y() != Double.parseDouble(p[13]) || hit.normal().z() != Double.parseDouble(p[14]))
                throw new AssertionError("Saved independent first-object mismatch: " + p[0] + " => " + hit);
            System.out.println(p[0]+"\t"+hit.x()+"\t"+hit.y()+"\t"+hit.z()+"\t"+hit.travel()+"\t"+hit.cell().blockId());
            replayed++;
        }
        if (replayed != 32) throw new AssertionError("Expected 16 actual refracted + 16 independent camera rays");
        System.out.println("PASS 32 actual saved-world geometry rays; no live Minecraft/GPU/material-radiance claim");
    }
}
