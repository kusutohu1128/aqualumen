package dev.aqualumen.atlas;
import java.util.*;
public final class FinalSnapshotTest {
    static class Fake implements FinalSnapshot.Boundary {
        int current=10,kind=5126,width=1600;boolean moved=false;
        public int program(){return current;} public int frame(){return 5;}
        public int[] viewport(){return new int[]{0,0,1600,900};}
        public FinalSnapshot.Scalar scalar(int p,String name){return new FinalSnapshot.Scalar(1,kind,1,name.equals("viewWidth")?width:900);}
        public Map<Integer,String> sources(int p){if(moved)current++;return Map.of(35633,"SYNTHETIC vertex",35632,"SYNTHETIC fragment");}
        public String renderer(){return "NVIDIA SYNTHETIC";}public String version(){return "SYNTHETIC GL";}
    }
    static void check(boolean b){if(!b)throw new AssertionError();}
    public static void main(String[] args){
        check(Boolean.TRUE.equals(FinalSnapshot.capture(10,new Fake()).get("available")));
        for(int mode=0;mode<4;mode++){Fake f=new Fake();if(mode==0)f.current=11;if(mode==1)f.kind=5124;if(mode==2)f.width=2560;if(mode==3)f.moved=true;check(Boolean.FALSE.equals(FinalSnapshot.capture(10,f).get("available")));}
        var value=FinalSnapshot.capture(10,new Fake());check(value.get("atlasTexelAddressesObserved").equals(false));check(value.get("drawIssuedProven").equals(false));
        System.out.println("PASS synthetic FINAL source/view protocol; no GL executed");
    }
}
