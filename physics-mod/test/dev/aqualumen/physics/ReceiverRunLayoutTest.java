package dev.aqualumen.physics;

public final class ReceiverRunLayoutTest {
    private static final ReceiverRunLayout.Cell unknown=new ReceiverRunLayout.Cell(0,0,0,0);
    private static final ReceiverRunLayout.Cell water=new ReceiverRunLayout.Cell(2,0,0,0);
    private static final ReceiverRunLayout.Cell opaque=new ReceiverRunLayout.Cell(3,0,0,0);
    private static void check(boolean condition) {
        if(!condition) throw new AssertionError("Receiver run mapping mismatch");
    }
    private static ReceiverRunLayout.Cell sample(int x,int y,int z) {
        if(y==10) return opaque;
        if(y>10 && y<29) return water;
        if(y==29) return new ReceiverRunLayout.Cell(4,1.8888889f,1,1);
        if(y==30) return new ReceiverRunLayout.Cell(4,.8888889f,1,1);
        if(y==31) return new ReceiverRunLayout.Cell(5,-.1111111f,1,1);
        return unknown;
    }
    public static void main(String[] arguments) {
        int[] reads={0};
        var layout=ReceiverRunLayout.capture(95,36,95,(x,y,z)-> { reads[0]++; return sample(x,y,z); });
        check(reads[0]==95*36*95);
        check(layout.runCount()==95*95*7 && layout.runCount()<=65536);
        for(int z=0;z<95;z++) for(int x=0;x<95;x++) for(int y=0;y<36;y++) {
            check(layout.cell(x,y,z).equals(sample(x,y,z)));
            check(layout.sourceIndex(x,y,z)==(y==10?x+95*(y*95+z):-1));
        }
        var interrupted=ReceiverRunLayout.capture(1,6,1,(x,y,z)->y==2?unknown:y==3 || y==4?opaque:water);
        check(interrupted.runCount()==5);
        check(interrupted.cell(0,2,0).equals(unknown));
        check(interrupted.sourceIndex(0,3,0)!=interrupted.sourceIndex(0,4,0));
        var buried=ReceiverRunLayout.capture(95,36,95,(x,y,z)->y<10?new ReceiverRunLayout.Cell(3,0,0,0,false):sample(x,y,z));
        check(buried.runCount()==63175);
        check(buried.cell(94,9,94).kind()==3 && buried.sourceIndex(94,9,94)==-1);
        check(buried.sourceIndex(94,10,94)==94+95*(10*95+94));
        float[] headers=layout.headers(),ranges=layout.ranges(),geometry=layout.geometry();
        headers[0]=-1; ranges[0]=-1; geometry[0]=Float.NaN;
        check(layout.headers()[0]==0 && layout.ranges()[0]==0 && layout.geometry()[0]==0);
        try { ReceiverRunLayout.capture(96,64,96,(x,y,z)->(y&1)==0?water:unknown); throw new AssertionError("Capacity exceeded"); }
        catch(IllegalArgumentException expected) { }
        try { layout.cell(95,0,0); throw new AssertionError("Outside window admitted"); }
        catch(IllegalArgumentException expected) { }
        try { new ReceiverRunLayout.Cell(4,Float.NaN,1,1); throw new AssertionError("Nonfinite geometry admitted"); }
        catch(IllegalArgumentException expected) { }
        System.out.println("PASS 95x36x95 lossless geometry runs: 324900 cells -> 63175 records; unknown/opaque/interface/source-address/extent controls; CPU only, not live capture or GPU transport");
    }
}
