package dev.aqualumen.physics;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Objects;

public final class ReceiverRunSourceCapture {
    public record Timings(long collection,long shading,long validation,long packing) {
        public Timings {
            if(collection<0 || shading<0 || validation<0 || packing<0)throw new IllegalArgumentException("Invalid receiver timing");
        }
    }
    public record Result(ReceiverRunPublisher.Window window,ReceiverRunLayout layout,ReceiverRunRadiance radiance,Timings timings) { }
    private ReceiverRunSourceCapture() { }
    public static int cacheCapacity(ReceiverRunPublisher.Window window) {
        Objects.requireNonNull(window);
        return (window.width()+4)*(window.height()+6)*(window.depth()+4);
    }
    private static ReceiverRunLayout.Cell unknown(boolean annotate,int code) {
        return new ReceiverRunLayout.Cell(0,annotate?code:0,0,0);
    }
    private static int unknownKind(ReceiverField.Cell cell) {
        return switch(cell.kind()) {
            case AIR -> 3;
            case WATER -> 8;
            case UNKNOWN -> 9;
            case UNSUPPORTED -> switch(cell.blockId()) {
                case "minecraft:seagrass" -> 4;
                case "minecraft:tall_seagrass" -> 5;
                case "minecraft:kelp","minecraft:kelp_plant" -> 6;
                default -> 7;
            };
            case OPAQUE -> throw new IllegalArgumentException("Opaque cells cannot be annotated unknown");
        };
    }
    private static ReceiverRunLayout.Cell read(ReceiverSourceVolume.World world,int x,int y,int z,boolean annotateUnknown) {
        if(!world.loaded(x,z))return unknown(annotateUnknown,1);
        if(y<world.minY() || y>=world.maxY())return unknown(annotateUnknown,2);
        var cell=world.receiverCell(x,y,z);
        if(cell.kind()==ReceiverField.Kind.OPAQUE)
            return new ReceiverRunLayout.Cell(3,0,0,0,y+1<world.maxY() && world.fullWater(x,y+1,z));
        if(cell.kind()==ReceiverField.Kind.WATER) {
            if(world.fullWater(x,y,z))return new ReceiverRunLayout.Cell(2,0,0,0);
            float height=world.partialWaterHeight(x,y,z);
            if(Float.isFinite(height) && height>0 && height<2 && height!=1)return new ReceiverRunLayout.Cell(4,height,1,1);
        } else if(cell.kind()==ReceiverField.Kind.AIR) {
            float height=world.upperWaterHeight(x,y,z);
            if(Float.isFinite(height) && height>-1 && height<0)return new ReceiverRunLayout.Cell(5,height,1,1);
        }
        return unknown(annotateUnknown,annotateUnknown?unknownKind(cell):0);
    }
    public static Result capture(ReceiverSourceVolume.World world,ReceiverRunPublisher.Window window,ReceiverRadianceVolume.Epoch epoch) {
        return capture(world,window,epoch,false);
    }
    public static Result capture(ReceiverSourceVolume.World world,ReceiverRunPublisher.Window window,ReceiverRadianceVolume.Epoch epoch,boolean annotateUnknown) {
        Objects.requireNonNull(world);Objects.requireNonNull(window);Objects.requireNonNull(epoch);
        long started=System.nanoTime();
        var identities=new HashMap<Integer,ReceiverField.Cell>();
        var layout=ReceiverRunLayout.capture(window.width(),window.height(),window.depth(),(x,y,z)-> {
            int wx=window.x()+x,wy=window.y()+y,wz=window.z()+z;
            var geometry=read(world,wx,wy,wz,annotateUnknown);
            if(geometry.sourceEligible())identities.put(x+window.width()*(y*window.depth()+z),world.receiverCell(wx,wy,wz));
            return geometry;
        });
        float[] ranges=layout.ranges();var addresses=new ArrayList<Integer>();var tops=new ArrayList<ReceiverSourceVolume.Top>();
        for(int record=0;record<layout.runCount();record++) {
            int address=(int)ranges[record*4+2];if(address<0)continue;
            int x=address%window.width(),row=address/window.width(),z=row%window.depth(),y=row/window.depth();
            addresses.add(address);tops.add(new ReceiverSourceVolume.Top(window.x()+x,window.y()+y,window.z()+z));
        }
        long collected=System.nanoTime();
        var supplied=world.shadeTops(List.copyOf(tops));
        if(supplied==null || supplied.size()!=tops.size())throw new IllegalStateException("Receiver run source batch extent mismatch");
        var samples=new HashMap<Integer,ReceiverRunRadiance.Sample>();
        for(int index=0;index<tops.size();index++) {
            var item=supplied.get(index);int address=addresses.get(index);
            if(item==null || !tops.get(index).equals(item.top()))throw new IllegalStateException("Receiver run source batch ownership mismatch");
            var surface=item.surface();
            if(surface==null || surface.epoch().world()!=epoch.world() || surface.epoch().frame()!=epoch.frame()
                || surface.epoch().resources()!=epoch.resources() || !identities.get(address).blockId().equals(surface.blockId()))continue;
            float[] total=surface.total(),sun=surface.sun();
            if(total[3]!=1 || sun[3]!=1)continue;
            samples.put(address,new ReceiverRunRadiance.Sample(epoch,address,total,sun,new float[]{0,1,0,1}));
        }
        long shaded=System.nanoTime();
        world.beginValidation();
        for(int z=0;z<window.depth();z++)for(int x=0;x<window.width();x++)for(int y=0;y<window.height();y++) {
            int wx=window.x()+x,wy=window.y()+y,wz=window.z()+z,address=x+window.width()*(y*window.depth()+z);
            if(!layout.cell(x,y,z).equals(read(world,wx,wy,wz,annotateUnknown))
                || identities.containsKey(address) && !identities.get(address).equals(world.receiverCell(wx,wy,wz)))
                throw new IllegalStateException("Receiver run geometry changed before publication");
        }
        long validated=System.nanoTime();
        var radiance=ReceiverRunRadiance.capture(layout,epoch,samples::get);
        return new Result(window,layout,radiance,new Timings(collected-started,shaded-collected,validated-shaded,System.nanoTime()-validated));
    }
}
