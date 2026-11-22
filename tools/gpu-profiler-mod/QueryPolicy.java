package dev.aqualumen.profiler;

/** Minecraft can render a nested loading screen while handling a world-change packet. */
final class QueryPolicy {
    private int depth;
    boolean enter(){return ++depth==1;}
    boolean outer(){return depth==1;}
    void leave(){
        if(depth==0) throw new IllegalStateException("frame exit without entry");
        depth--;
    }
    static boolean harvest(long frame,long issued,int lag){return issued!=0 && frame-issued>=lag;}
    static boolean room(int markers,int open,int limit){return markers+open+2<=limit;}
}
