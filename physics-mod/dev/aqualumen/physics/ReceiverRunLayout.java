package dev.aqualumen.physics;

import java.util.ArrayList;
import java.util.Objects;

public final class ReceiverRunLayout {
    public record Cell(float kind,float height,float qualified,float ready,boolean sourceEligible) {
        public Cell(float kind,float height,float qualified,float ready) {
            this(kind,height,qualified,ready,kind==3);
        }
        public Cell {
            if(!Float.isFinite(kind) || !Float.isFinite(height) || !Float.isFinite(qualified) || !Float.isFinite(ready)
                    || kind!=0 && kind!=2 && kind!=3 && kind!=4 && kind!=5)
                throw new IllegalArgumentException("Unsupported run geometry");
            if(kind==4 && (height<=0 || height>=2 || height==1 || qualified!=1 || ready!=1)
                    || kind==5 && (height<=-1 || height>=0 || qualified!=1 || ready!=1))
                throw new IllegalArgumentException("Unqualified run interface");
            if(sourceEligible && kind!=3)throw new IllegalArgumentException("Nonopaque run cannot own a source address");
        }
    }
    public interface Geometry { Cell cell(int x,int y,int z); }
    private record Run(int first,int length,Cell cell,int sourceIndex) { }
    private final int width,height,depth;
    private final int[] starts,counts;
    private final Run[] runs;
    private ReceiverRunLayout(int width,int height,int depth,int[] starts,int[] counts,Run[] runs) {
        this.width=width; this.height=height; this.depth=depth;
        this.starts=starts; this.counts=counts; this.runs=runs;
    }
    public static ReceiverRunLayout capture(int width,int height,int depth,Geometry geometry) {
        if(width<1 || height<1 || depth<1 || width>96 || height>64 || depth>96)
            throw new IllegalArgumentException("Run window exceeds bounded extent");
        Objects.requireNonNull(geometry);
        int[] starts=new int[width*depth],counts=new int[width*depth];
        var runs=new ArrayList<Run>();
        for(int z=0;z<depth;z++) for(int x=0;x<width;x++) {
            int column=x+width*z; starts[column]=runs.size();
            Cell previous=null; int first=0,length=0;
            for(int y=0;y<height;y++) {
                Cell cell=Objects.requireNonNull(geometry.cell(x,y,z));
                boolean merge=cell.equals(previous) && (cell.kind()==0 || cell.kind()==2 || cell.kind()==3 && !cell.sourceEligible());
                if(merge) { length++; continue; }
                if(previous!=null) append(runs,new Run(first,length,previous,
                    previous.sourceEligible()?x+width*(first*depth+z):-1));
                previous=cell; first=y; length=1;
            }
            append(runs,new Run(first,length,previous,previous.sourceEligible()?x+width*(first*depth+z):-1));
            counts[column]=runs.size()-starts[column];
        }
        return new ReceiverRunLayout(width,height,depth,starts,counts,runs.toArray(Run[]::new));
    }
    private static void append(ArrayList<Run> runs,Run run) {
        if(runs.size()>=65536) throw new IllegalArgumentException("Compressed receiver exceeds bounded capacity");
        runs.add(run);
    }
    private Run find(int x,int y,int z) {
        if(x<0 || x>=width || y<0 || y>=height || z<0 || z>=depth)
            throw new IllegalArgumentException("Receiver run lookup outside window");
        int column=x+width*z,low=starts[column],high=low+counts[column]-1;
        while(low<=high) {
            int middle=(low+high)>>>1; Run run=runs[middle];
            if(y<run.first()) high=middle-1;
            else if(y>=run.first()+run.length()) low=middle+1;
            else return run;
        }
        throw new IllegalStateException("Receiver column has a gap");
    }
    public Cell cell(int x,int y,int z) { return find(x,y,z).cell(); }
    public int sourceIndex(int x,int y,int z) { return find(x,y,z).sourceIndex(); }
    public int runCount() { return runs.length; }
    public int width() { return width; }
    public int height() { return height; }
    public int depth() { return depth; }
    public float[] headers() {
        float[] values=new float[starts.length*4];
        for(int column=0;column<starts.length;column++) {
            values[column*4]=starts[column]; values[column*4+1]=counts[column];
        }
        return values;
    }
    public float[] ranges() {
        float[] values=new float[runs.length*4];
        for(int index=0;index<runs.length;index++) {
            Run run=runs[index]; values[index*4]=run.first(); values[index*4+1]=run.length();
            values[index*4+2]=run.sourceIndex();
        }
        return values;
    }
    public float[] geometry() {
        float[] values=new float[runs.length*4];
        for(int index=0;index<runs.length;index++) {
            Cell cell=runs[index].cell();
            values[index*4]=cell.kind(); values[index*4+1]=cell.height();
            values[index*4+2]=cell.qualified(); values[index*4+3]=cell.ready();
        }
        return values;
    }
}
