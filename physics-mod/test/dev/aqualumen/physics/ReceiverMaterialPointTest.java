package dev.aqualumen.physics;

public final class ReceiverMaterialPointTest {
    public static void main(String[] arguments) {
        var epoch=new ReceiverRadianceVolume.Epoch(new Object(),7,2);
        var attributes=new ReceiverVertexShader.Output(.2f,.4f,.1f,.9f,.3f,.5f,.7f,.8f);
        var point=new ReceiverMaterialPoint(epoch,-17.25,63.125,31.5,1,0,0,attributes);
        if(point.attributes()!=attributes || point.x()!=-17.25 || point.normalX()!=1)
            throw new AssertionError("Material point changed supplied geometry/material");
        for(float normal:new float[]{0,2,Float.NaN,Float.POSITIVE_INFINITY})
            rejects(()->new ReceiverMaterialPoint(epoch,0,0,0,normal,0,0,attributes));
        rejects(()->new ReceiverMaterialPoint(epoch,Double.NaN,0,0,0,1,0,attributes));
        rejects(()->new ReceiverMaterialPoint(epoch,0,0,0,0,1,0,
                new ReceiverVertexShader.Output(-.1f,.4f,.1f,.9f,.3f,.5f,.7f,.8f)));
        System.out.println("PASS material point supplied attributes/position/normal and malformed negatives; CPU only");
    }
    private static void rejects(Runnable action) {
        try {action.run();throw new AssertionError("Malformed material admitted");}
        catch(IllegalArgumentException expected) {}
    }
}
