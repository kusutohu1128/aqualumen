package dev.aqualumen.bench;

import java.util.List;
import java.util.Properties;

/** CPU policy controls only: this never opens Minecraft or an OpenGL context. */
public final class ShoreRuntimeGuardsTest {
    public static void main(String[] args) {
        String id="b22dbccb-2970-41e6-847f-f183b1ec923d";
        var accepted=new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",id,308060,"minecraft:overworld",true,true);
        require(ShoreRuntimeObserver.acceptsScope(accepted),"Exact offline local candidate scope accepts");
        for(var scope:List.of(
                new BathymetrySnapshot.Scope(false,true,false,1,true,"AqualumenNaturalV2",id,308060,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,true,1,true,"AqualumenNaturalV2",id,308060,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,false,2,true,"AqualumenNaturalV2",id,308060,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,false,1,false,"AqualumenNaturalV2",id,308060,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,false,1,true,"Ordinary",id,308060,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2","wrong",308060,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",id,308061,"minecraft:overworld",true,true),
                new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",id,308060,"minecraft:the_nether",true,true),
                new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",id,308060,"minecraft:overworld",false,true),
                new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",id,308060,"minecraft:overworld",true,false)))
            require(!ShoreRuntimeObserver.acceptsScope(scope),"Unapproved live scope stays inert");
        Properties config=new Properties();
        config.setProperty("schema","2");config.setProperty("world","AqualumenNaturalV2");config.setProperty("world_id",id);
        config.setProperty("expected_pack","Aqualumen-ShoreProbe-world-r3.zip");
        config.setProperty("expected_pack_sha256","0".repeat(64));
        require(ShoreRuntimeObserver.acceptsConfiguration(config),"Explicit world diagnostic identity accepts");
        for(String name:List.of("Aqualumen-0.6.0.zip","Aqualumen-ShoreProbe-transport-r2.zip","../Aqualumen-ShoreProbe-world-r3.zip")) {
            config.setProperty("expected_pack",name);
            require(!ShoreRuntimeObserver.acceptsConfiguration(config),"Ordinary or unrelated pack stays inert");
        }
        require(ShoreRuntimeObserver.parseTexels("0:0,1599:899",1600,900).equals(
                List.of(new ShoreSamplerSnapshot.Texel(0,0),new ShoreSamplerSnapshot.Texel(1599,899))),"Native bottom-left integer coordinates preserved");
        for(String invalid:List.of("","-1:0","1600:0","0:900","1:2,1:2","1.0:2","0:0,")) {
            try {ShoreRuntimeObserver.parseTexels(invalid,1600,900);throw new AssertionError("Invalid selection accepted");}
            catch(IllegalArgumentException expected) { }
        }
        System.out.println("PASS shore runtime CPU guards; no real GL or scope acceptance evidence");
    }
    private static void require(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
}
