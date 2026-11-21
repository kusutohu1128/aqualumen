package dev.aqualumen.physics;

import java.util.concurrent.atomic.AtomicBoolean;

public final class ReceiverVoxelCacheTest {
    public static void main(String[] arguments) throws InterruptedException {
        int width=91,height=42,depth=91,count=width*height*depth;
        var cache=new ReceiverVoxelCache<Integer>(403,29,-429,width,height,depth);
        for(int offsetY=0;offsetY<height;offsetY++) for(int offsetZ=0;offsetZ<depth;offsetZ++) for(int offsetX=0;offsetX<width;offsetX++) {
            int expected=(offsetY*depth+offsetZ)*width+offsetX;
            check(cache.get(403+offsetX,29+offsetY,-429+offsetZ,()->expected)==expected,"Exact coordinate index");
        }
        check(cache.reads()==count,"Every padded cell read exactly once");
        for(int offsetY=0;offsetY<height;offsetY++) for(int offsetZ=0;offsetZ<depth;offsetZ++) for(int offsetX=0;offsetX<width;offsetX++) {
            int expected=(offsetY*depth+offsetZ)*width+offsetX;
            check(cache.get(403+offsetX,29+offsetY,-429+offsetZ,()->{throw new AssertionError("Repeated backend read");})==expected,
                    "Repeated coordinate retains exact cached owner");
        }
        cache.beginValidation();
        for(int offsetY=0;offsetY<height;offsetY++) for(int offsetZ=0;offsetZ<depth;offsetZ++) for(int offsetX=0;offsetX<width;offsetX++) {
            int changed=(offsetY*depth+offsetZ)*width+offsetX+count;
            check(cache.get(403+offsetX,29+offsetY,-429+offsetZ,()->changed)==changed,"Validation reads fresh changed values");
        }
        check(cache.reads()==count*2,"Fresh validation does not reuse collection values");
        for(int[] outside:new int[][]{{402,29,-429},{494,29,-429},{403,28,-429},{403,71,-429},
                {403,29,-430},{403,29,-338},{Integer.MIN_VALUE,29,-429},{Integer.MAX_VALUE,29,-429}}) {
            boolean rejected=false;
            try { cache.get(outside[0],outside[1],outside[2],()->{throw new AssertionError("Outside extent reached backend");}); }
            catch(IllegalStateException expected) { rejected=true; }
            check(rejected,"Outside extent fails before backend read");
        }
        var wrongThread=new AtomicBoolean();
        var worker=new Thread(()-> {
            try { cache.get(403,29,-429,()->0); } catch(IllegalStateException expected) { wrongThread.set(true); }
        });
        worker.start();worker.join();check(wrongThread.get(),"Another thread cannot read cached data");
        cache.close();cache.close();
        boolean closed=false;
        try { cache.beginValidation(); } catch(IllegalStateException expected) { closed=true; }
        check(closed,"Closed cache cannot restart a phase");
        try(var extreme=new ReceiverVoxelCache<Integer>(Integer.MIN_VALUE,Integer.MAX_VALUE,-1,1,1,1)) {
            check(extreme.get(Integer.MIN_VALUE,Integer.MAX_VALUE,-1,()->7)==7,"Exact extreme coordinate owner");
        }
        for(int[] invalid:new int[][]{{0,0,0,0,1,1},{0,0,0,101,1,1},{0,0,0,1,71,1},
                {0,0,0,1,1,101},{Integer.MAX_VALUE,0,0,2,1,1},{0,Integer.MAX_VALUE,0,1,2,1}}) {
            boolean rejected=false;
            try { new ReceiverVoxelCache<Integer>(invalid[0],invalid[1],invalid[2],invalid[3],invalid[4],invalid[5]); }
            catch(IllegalArgumentException expected) { rejected=true; }
            check(rejected,"Invalid bounded extent rejected");
        }
        try(var flags=new ReceiverVoxelCache<Boolean>(0,0,0,1,1,1)) {
            check(!flags.get(0,0,0,()->false),"False is a valid cached value");
            check(!flags.get(0,0,0,()->true) && flags.reads()==1,"False is not mistaken for a miss");
        }
        try(var failures=new ReceiverVoxelCache<Integer>(0,0,0,1,1,1)) {
            boolean nullRejected=false;
            try { failures.get(0,0,0,()->null); } catch(NullPointerException expected) { nullRejected=true; }
            check(nullRejected && failures.reads()==0,"Missing backend result does not become ready");
            check(failures.get(0,0,0,()->9)==9 && failures.reads()==1,"Failed read leaves no stale entry");
        }
        System.out.println("PASS indexed voxel cache: all "+count+" padded cells, repeated queries, fresh validation, extent-before-read, signed/extreme coordinates, missing/false values, thread and closed guards; CPU only");
    }
    private static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
}
