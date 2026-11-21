package dev.aqualumen.physics;

public final class ReceiverMaterialTriangleTest {
    public static void main(String[] arguments) {
        var epoch=new ReceiverRadianceVolume.Epoch(new Object(),7,2);
        var low=new ReceiverVertexShader.Output(0,0,0,0,0,0,0,0);
        var high=new ReceiverVertexShader.Output(1,1,1,1,1,1,1,1);
        var first=new ReceiverMaterialTriangle.Vertex(-17,62,31,low);
        var second=new ReceiverMaterialTriangle.Vertex(-15,62,31,high);
        var third=new ReceiverMaterialTriangle.Vertex(-17,64,31,low);
        var triangle=new ReceiverMaterialTriangle(epoch,first,second,third);
        var point=triangle.sample(.25,.5,.25,false);
        if(point.x()!=-16 || point.y()!=62.5 || point.z()!=31 || point.normalZ()!=1
                || point.attributes().u()!=.5 || point.attributes().ao()!=.5 || point.epoch()!=epoch)
            throw new AssertionError("Barycentric material/world geometry changed");
        if(triangle.sample(.25,.5,.25,true).normalZ()!=-1)
            throw new AssertionError("Explicit reversed face normal lost");
        if(!triangle.sample(0,1,0,false).attributes().equals(high))
            throw new AssertionError("Vertex endpoint attributes changed");
        rejects(()->triangle.sample(-.1,.5,.6,false));
        rejects(()->triangle.sample(.2,.2,.2,false));
        rejects(()->triangle.sample(Double.NaN,.5,.5,false));
        rejects(()->new ReceiverMaterialTriangle(epoch,first,first,third));
        var varied=new ReceiverMaterialTriangle(epoch,
                new ReceiverMaterialTriangle.Vertex(0,0,0,new ReceiverVertexShader.Output(0,.1f,.2f,.3f,.4f,.5f,.6f,.7f)),
                new ReceiverMaterialTriangle.Vertex(2,0,0,new ReceiverVertexShader.Output(.8f,.7f,.6f,.5f,.4f,.3f,.2f,.1f)),
                new ReceiverMaterialTriangle.Vertex(0,2,0,new ReceiverVertexShader.Output(.1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f)));
        var mixed=varied.sample(.2,.3,.5,false).attributes();
        float[] actual={mixed.u(),mixed.v(),mixed.block(),mixed.sky(),mixed.red(),mixed.green(),mixed.blue(),mixed.ao()};
        double[] expected={.29,.33,.37,.41,.45,.49,.53,.57};
        for(int channel=0;channel<8;channel++)
            if(Math.abs(actual[channel]-expected[channel])>1e-6)
                throw new AssertionError("Distinct material channel interpolation changed");
        System.out.println("PASS material triangle interpolation, vertical geometry, reversal, endpoints and malformed negatives; CPU only");
    }
    private static void rejects(Runnable action) {
        try {action.run();throw new AssertionError("Malformed material triangle admitted");}
        catch(IllegalArgumentException expected) {}
    }
}
