package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;

public final class ReceiverQuadIntersection {
    public record Point(double x, double y, double z, double u, double v) {
        public Point {
            if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)
                    || !Double.isFinite(u) || !Double.isFinite(v))
                throw new IllegalArgumentException("Nonfinite receiver vertex");
        }
    }
    public record Ray(double x, double y, double z, double dx, double dy, double dz, double limit) {
        public Ray {
            if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)
                    || !Double.isFinite(dx) || !Double.isFinite(dy) || !Double.isFinite(dz)
                    || !Double.isFinite(limit) || limit <= 0
                    || Math.abs(dx * dx + dy * dy + dz * dz - 1) > 1e-9)
                throw new IllegalArgumentException("Receiver ray requires a unit direction and finite range");
        }
    }
    public enum Coverage { TRANSPARENT, OPAQUE, UNKNOWN }
    @FunctionalInterface
    public interface Alpha { Coverage sample(double u, double v); }
    public record Quad(Point first, Point second, Point third, Point fourth, Alpha alpha) {
        public Quad {
            Objects.requireNonNull(first); Objects.requireNonNull(second);
            Objects.requireNonNull(third); Objects.requireNonNull(fourth); Objects.requireNonNull(alpha);
        }
    }
    public record Hit(double distance, double u, double v, int primitive, Coverage coverage) {}

    private ReceiverQuadIntersection() {}

    public static Hit first(Ray ray, List<Quad> quads) {
        Objects.requireNonNull(ray);
        List<Quad> owned = List.copyOf(quads);
        Hit nearest = null;
        for (int index = 0; index < owned.size(); index++) {
            Quad quad = owned.get(index);
            Hit first = triangle(ray, quad.first(), quad.second(), quad.third(), index);
            Hit second = triangle(ray, quad.first(), quad.third(), quad.fourth(), index);
            for (Hit candidate : new Hit[] {first, second}) {
                if (candidate == null || nearest != null && candidate.distance() > nearest.distance()) continue;
                Coverage coverage = Objects.requireNonNull(quad.alpha().sample(candidate.u(), candidate.v()));
                if (coverage == Coverage.TRANSPARENT) continue;
                if (nearest == null || candidate.distance() < nearest.distance()
                        || coverage == Coverage.UNKNOWN && candidate.distance() == nearest.distance())
                    nearest = new Hit(candidate.distance(), candidate.u(), candidate.v(), index, coverage);
            }
        }
        return nearest;
    }

    private static Hit triangle(Ray ray, Point first, Point second, Point third, int primitive) {
        double edgeX = second.x() - first.x(), edgeY = second.y() - first.y(), edgeZ = second.z() - first.z();
        double otherX = third.x() - first.x(), otherY = third.y() - first.y(), otherZ = third.z() - first.z();
        double crossX = ray.dy() * otherZ - ray.dz() * otherY;
        double crossY = ray.dz() * otherX - ray.dx() * otherZ;
        double crossZ = ray.dx() * otherY - ray.dy() * otherX;
        double determinant = edgeX * crossX + edgeY * crossY + edgeZ * crossZ;
        if (!Double.isFinite(determinant) || Math.abs(determinant) < 1e-12) return null;
        double offsetX = ray.x() - first.x(), offsetY = ray.y() - first.y(), offsetZ = ray.z() - first.z();
        double weightSecond = (offsetX * crossX + offsetY * crossY + offsetZ * crossZ) / determinant;
        double normalX = offsetY * edgeZ - offsetZ * edgeY;
        double normalY = offsetZ * edgeX - offsetX * edgeZ;
        double normalZ = offsetX * edgeY - offsetY * edgeX;
        double weightThird = (ray.dx() * normalX + ray.dy() * normalY + ray.dz() * normalZ) / determinant;
        if (!Double.isFinite(weightSecond) || !Double.isFinite(weightThird)
                || weightSecond < 0 || weightThird < 0 || weightSecond + weightThird > 1) return null;
        double distance = (otherX * normalX + otherY * normalY + otherZ * normalZ) / determinant;
        if (!Double.isFinite(distance) || distance <= 0 || distance > ray.limit()) return null;
        double weightFirst = 1 - weightSecond - weightThird;
        double textureU = first.u() * weightFirst + second.u() * weightSecond + third.u() * weightThird;
        double textureV = first.v() * weightFirst + second.v() * weightSecond + third.v() * weightThird;
        if (!Double.isFinite(textureU) || !Double.isFinite(textureV)) return null;
        return new Hit(distance, textureU, textureV, primitive, Coverage.UNKNOWN);
    }
}
