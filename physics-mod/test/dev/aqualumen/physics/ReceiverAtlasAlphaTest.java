package dev.aqualumen.physics;

public final class ReceiverAtlasAlphaTest {
    private static void check(boolean condition) {
        if (!condition) throw new AssertionError("Atlas alpha sampling contract failed");
    }
    public static void main(String[] arguments) {
        byte[] values = {0,(byte)255,(byte)255,0};
        var image = new ReceiverAtlasAlpha(2,2,values);
        values[0] = (byte)255;
        var clamp = ReceiverAtlasAlpha.Wrap.CLAMP;
        var repeat = ReceiverAtlasAlpha.Wrap.REPEAT;
        var nearest = ReceiverAtlasAlpha.Filter.NEAREST;
        var linear = ReceiverAtlasAlpha.Filter.LINEAR;
        check(image.sampleBaseLevel(.25,.25,nearest,clamp,clamp) == 0);
        check(image.sampleBaseLevel(.75,.25,nearest,clamp,clamp) == 1);
        check(image.sampleBaseLevel(.25,.75,nearest,clamp,clamp) == 1);
        check(image.sampleBaseLevel(.5,.5,linear,clamp,clamp) == .5);
        check(image.sampleBaseLevel(1.25,.25,nearest,repeat,repeat) == 0);
        check(image.sampleBaseLevel(-.25,.25,nearest,repeat,repeat) == 1);
        check(image.sampleBaseLevel(1,.25,nearest,clamp,clamp) == 1);
        check(image.sampleBaseLevel(0,.25,linear,repeat,repeat) == .5);
        check(Double.isNaN(image.sampleBaseLevel(Double.NaN,0,linear,clamp,clamp)));
        try {
            new ReceiverAtlasAlpha(2,2,new byte[3]);
            throw new AssertionError("Malformed atlas admitted");
        } catch (IllegalArgumentException expected) {}
        System.out.println("Atlas alpha CPU: immutable bytes, orientation, nearest/linear and wrap boundaries verified; base level only");
    }
}
