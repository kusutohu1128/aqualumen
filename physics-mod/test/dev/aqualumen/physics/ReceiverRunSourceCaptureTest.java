package dev.aqualumen.physics;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class ReceiverRunSourceCaptureTest {
    private static final ReceiverRadianceVolume.Epoch epoch=new ReceiverRadianceVolume.Epoch(new Object(),3,2);
    private static final ReceiverRunPublisher.Window window=new ReceiverRunPublisher.Window(0,0,0,5,6,5);
    private static final class World implements ReceiverSourceVolume.World {
        boolean edit,drift,unload,reorder,missing,shaded;
        int validations;
        public boolean loaded(int x,int z) { return !(unload && shaded); }
        public int minY() { return 0; }
        public int maxY() { return 6; }
        public ReceiverField.Cell receiverCell(int x,int y,int z) {
            if(!loaded(x,z))throw new AssertionError("Unloaded world read");
            return y<2?new ReceiverField.Cell(ReceiverField.Kind.OPAQUE,edit && shaded?"minecraft:stone":"minecraft:sand")
                :y<5?new ReceiverField.Cell(ReceiverField.Kind.WATER,"minecraft:water")
                :new ReceiverField.Cell(ReceiverField.Kind.AIR,"minecraft:air");
        }
        public boolean fullWater(int x,int y,int z) { return y==2; }
        public float partialWaterHeight(int x,int y,int z) {
            float height=drift && shaded?.7f:.8888889f;
            return y==3?1+height:y==4?height:0;
        }
        public float upperWaterHeight(int x,int y,int z) { return y==5?partialWaterHeight(x,4,z)-1:0; }
        public ReceiverSourceVolume.Surface shadeTop(int x,int y,int z) {
            return missing?null:new ReceiverSourceVolume.Surface(epoch,"minecraft:sand",new float[]{.75f,0,0,1},new float[]{.1f,0,0,1});
        }
        public List<ReceiverSourceVolume.ShadedTop> shadeTops(List<ReceiverSourceVolume.Top> tops) {
            var results=new ArrayList<ReceiverSourceVolume.ShadedTop>();
            for(var top:tops)results.add(new ReceiverSourceVolume.ShadedTop(top,shadeTop(top.x(),top.y(),top.z())));
            if(reorder)Collections.reverse(results);
            shaded=true;return results;
        }
        public void beginValidation() { validations++; }
    }
    public static void main(String[] arguments) {
        unknownKinds();
        var wideWindow=new ReceiverRunPublisher.Window(0,0,0,95,36,95);
        int capacity=ReceiverRunSourceCapture.cacheCapacity(wideWindow);
        if(capacity!=411642 || capacity>1048576)throw new AssertionError("Wide capture bound mismatch");
        try(var cache=new ReceiverCaptureCache<Integer,Integer>(capacity)) {
            for(int index=0;index<324900;index++) { int value=index;cache.get(index,()->value); }
            if(cache.reads()!=324900)throw new AssertionError("Wide capture cache coverage mismatch");
            cache.beginValidation();
            if(cache.get(0,()->-1)!=-1 || cache.reads()!=324901)throw new AssertionError("Wide cache reused collection value during audit");
        }
        try { new ReceiverCaptureCache<Integer,Integer>(1048577);throw new AssertionError("Unbounded wide cache admitted"); }
        catch(IllegalArgumentException expected) { }
        var world=new World();var result=ReceiverRunSourceCapture.capture(world,window,epoch);
        if(world.validations!=1 || result.layout().runCount()!=150 || !result.radiance().owns(result.layout()))throw new AssertionError("Capture ownership mismatch");
        if(result.timings().collection()<0 || result.timings().shading()<0 || result.timings().validation()<0 || result.timings().packing()<0)
            throw new AssertionError("Stage timing invalid");
        float[] cells=result.radiance().cells(),sources=result.radiance().source();int ready=0;
        for(int offset=0;offset<cells.length;offset+=4)if(sources[offset+3]==1)ready++;
        if(ready!=25 || result.layout().sourceIndex(0,0,0)!=-1)throw new AssertionError("Buried/source floor distinction mismatch");
        var missing=new World();missing.missing=true;
        for(float value:ReceiverRunSourceCapture.capture(missing,window,epoch).radiance().source())
            if(value!=0)throw new AssertionError("Missing source invented");
        for(int cause=0;cause<4;cause++) {
            var changed=new World();changed.edit=cause==0;changed.drift=cause==1;changed.unload=cause==2;changed.reorder=cause==3;
            try { ReceiverRunSourceCapture.capture(changed,window,epoch);throw new AssertionError("Changed or reordered capture admitted"); }
            catch(IllegalStateException expected) { }
        }
        System.out.println("PASS run source composition: qualified exposed tops, buried solids, paired source ownership and fresh edit/height/unload/order negatives; CPU only, not live wide-field capture");
    }
    private static final class UnknownWorld implements ReceiverSourceVolume.World {
        boolean drift,validation;
        public boolean loaded(int worldX,int worldZ) { return worldX!=0; }
        public int minY() { return 0; }
        public int maxY() { return 8; }
        public boolean fullWater(int worldX,int worldY,int worldZ) { return false; }
        public ReceiverField.Cell receiverCell(int worldX,int worldY,int worldZ) {
            if(worldX==0 || worldY<0)throw new AssertionError("Unloaded/outside cell read");
            return switch(worldX) {
                case 1 -> new ReceiverField.Cell(ReceiverField.Kind.AIR,"minecraft:air");
                case 2 -> new ReceiverField.Cell(ReceiverField.Kind.UNSUPPORTED,drift&&validation?"minecraft:glass":"minecraft:seagrass");
                case 3 -> new ReceiverField.Cell(ReceiverField.Kind.UNSUPPORTED,"minecraft:tall_seagrass");
                case 4 -> new ReceiverField.Cell(ReceiverField.Kind.UNSUPPORTED,"minecraft:kelp_plant");
                case 5 -> new ReceiverField.Cell(ReceiverField.Kind.UNSUPPORTED,"minecraft:glass");
                case 6 -> new ReceiverField.Cell(ReceiverField.Kind.WATER,"minecraft:water");
                case 7 -> ReceiverField.Cell.UNKNOWN;
                default -> new ReceiverField.Cell(ReceiverField.Kind.OPAQUE,"minecraft:sand");
            };
        }
        public ReceiverSourceVolume.Surface shadeTop(int worldX,int worldY,int worldZ) { throw new AssertionError("Unknown became a source"); }
        public void beginValidation() { validation=true; }
    }
    private static void unknownKinds() {
        var bounds=new ReceiverRunPublisher.Window(0,-1,0,9,3,1);
        var original=ReceiverRunSourceCapture.capture(new UnknownWorld(),bounds,epoch);
        var diagnostic=ReceiverRunSourceCapture.capture(new UnknownWorld(),bounds,epoch,true);
        int[] expected={1,3,4,5,6,7,8,9};
        for(int worldX=0;worldX<8;worldX++) {
            var plain=original.layout().cell(worldX,1,0);var tagged=diagnostic.layout().cell(worldX,1,0);
            if(plain.kind()!=0 || plain.height()!=0 || tagged.kind()!=0 || tagged.height()!=expected[worldX]
                    || tagged.sourceEligible() || tagged.qualified()!=0 || tagged.ready()!=0)
                throw new AssertionError("Unknown diagnostic changed admission or subtype");
        }
        if(diagnostic.layout().cell(1,0,0).height()!=2 || diagnostic.layout().cell(8,1,0).kind()!=3
                || diagnostic.layout().cell(8,1,0).height()!=0)
            throw new AssertionError("Outside/opaque diagnostic boundary mismatch");
        for(float value:diagnostic.radiance().source())if(value!=0)throw new AssertionError("Unknown annotation invented radiance");
        var changed=new UnknownWorld();changed.drift=true;
        try { ReceiverRunSourceCapture.capture(changed,bounds,epoch,true);throw new AssertionError("Unknown subtype drift was not validated"); }
        catch(IllegalStateException expectedDrift) { }
        System.out.println("PASS opt-in unknown subtypes: original zero tags, same unknown admission, no source/readiness, outside-before-read, fresh subtype drift rejection; CPU only");
    }
}
