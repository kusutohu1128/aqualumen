package dev.aqualumen.physics;

import java.util.Objects;

public final class ReceiverAtlasAlpha {
    public enum Filter { NEAREST, LINEAR }
    public enum Wrap { CLAMP, REPEAT }
    private final int width, height;
    private final byte[] alpha;

    public ReceiverAtlasAlpha(int width, int height, byte[] alpha) {
        if (width < 1 || height < 1 || (long)width * height > 16777216 || alpha.length != (long)width * height)
            throw new IllegalArgumentException("Unbounded atlas alpha extent");
        this.width = width; this.height = height; this.alpha = alpha.clone();
    }

    public double sampleBaseLevel(double textureU, double textureV, Filter filter, Wrap wrapU, Wrap wrapV) {
        Objects.requireNonNull(filter); Objects.requireNonNull(wrapU); Objects.requireNonNull(wrapV);
        if (!Double.isFinite(textureU) || !Double.isFinite(textureV)) return Double.NaN;
        double mappedU = map(textureU,wrapU), mappedV = map(textureV,wrapV);
        if (filter == Filter.NEAREST)
            return texel((int)Math.floor(mappedU * width),(int)Math.floor(mappedV * height),wrapU,wrapV);
        double coordinateX = mappedU * width - 0.5, coordinateY = mappedV * height - 0.5;
        int lowerX = (int)Math.floor(coordinateX), lowerY = (int)Math.floor(coordinateY);
        double fractionX = coordinateX - lowerX, fractionY = coordinateY - lowerY;
        double bottom = texel(lowerX,lowerY,wrapU,wrapV)*(1-fractionX) + texel(lowerX+1,lowerY,wrapU,wrapV)*fractionX;
        double top = texel(lowerX,lowerY+1,wrapU,wrapV)*(1-fractionX) + texel(lowerX+1,lowerY+1,wrapU,wrapV)*fractionX;
        return bottom*(1-fractionY)+top*fractionY;
    }

    private static double map(double coordinate, Wrap wrap) {
        return wrap == Wrap.REPEAT ? coordinate-Math.floor(coordinate) : Math.max(0,Math.min(1,coordinate));
    }
    private double texel(int x, int y, Wrap wrapU, Wrap wrapV) {
        int wrappedX = wrapU == Wrap.REPEAT ? Math.floorMod(x,width) : Math.max(0,Math.min(width-1,x));
        int wrappedY = wrapV == Wrap.REPEAT ? Math.floorMod(y,height) : Math.max(0,Math.min(height-1,y));
        return (alpha[wrappedY*width+wrappedX]&255)/255.0;
    }
    public int width() { return width; }
    public int height() { return height; }
}
