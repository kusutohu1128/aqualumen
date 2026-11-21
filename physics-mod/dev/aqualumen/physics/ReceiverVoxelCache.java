package dev.aqualumen.physics;

import java.util.Arrays;
import java.util.Objects;
import java.util.function.Supplier;

public final class ReceiverVoxelCache<Value> implements AutoCloseable {
    private final Thread owner=Thread.currentThread();
    private final int originX,originY,originZ,width,height,depth;
    private final Object[] values;
    private boolean closed;
    private int reads;

    public ReceiverVoxelCache(int originX,int originY,int originZ,int width,int height,int depth) {
        long count=(long)width*height*depth;
        if(width<1 || width>100 || height<1 || height>70 || depth<1 || depth>100 || count>1048576
                || (long)originX+width-1>Integer.MAX_VALUE || (long)originY+height-1>Integer.MAX_VALUE
                || (long)originZ+depth-1>Integer.MAX_VALUE)
            throw new IllegalArgumentException("Invalid voxel-cache extent");
        this.originX=originX;this.originY=originY;this.originZ=originZ;
        this.width=width;this.height=height;this.depth=depth;
        values=new Object[(int)count];
    }
    private void owner() {
        if(closed || Thread.currentThread()!=owner) throw new IllegalStateException("Voxel cache has no current owner");
    }
    private int index(int worldX,int worldY,int worldZ) {
        long offsetX=(long)worldX-originX,offsetY=(long)worldY-originY,offsetZ=(long)worldZ-originZ;
        if(offsetX<0 || offsetY<0 || offsetZ<0 || offsetX>=width || offsetY>=height || offsetZ>=depth)
            throw new IllegalStateException("Voxel cache extent exceeded");
        return (int)((offsetY*depth+offsetZ)*width+offsetX);
    }
    @SuppressWarnings("unchecked")
    public Value get(int worldX,int worldY,int worldZ,Supplier<Value> read) {
        owner();Objects.requireNonNull(read);
        int index=index(worldX,worldY,worldZ);
        Value value=(Value)values[index];
        if(value!=null) return value;
        value=Objects.requireNonNull(read.get());reads++;
        values[index]=value;return value;
    }
    public int reads() { owner();return reads; }
    public void beginValidation() { owner();Arrays.fill(values,null); }
    public void close() {
        if(Thread.currentThread()!=owner) throw new IllegalStateException("Voxel cache close outside owner");
        Arrays.fill(values,null);closed=true;
    }
}
