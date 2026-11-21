package dev.aqualumen.bench;

import java.nio.file.Path;
import java.util.List;
import java.util.zip.ZipFile;
import net.fabricmc.loader.api.metadata.ModMetadata;
import net.fabricmc.loader.impl.metadata.DependencyOverrides;
import net.fabricmc.loader.impl.metadata.ModMetadataParser;
import net.fabricmc.loader.impl.metadata.VersionOverrides;

/** Parse the actual packaged bridges with the pinned external Fabric loader. */
public final class BathymetryMetadataTest {
    public static void main(String[] args)throws Exception {
        Path overrides=Path.of(args[2]);
        ModMetadata candidate=read(Path.of(args[0]),overrides);
        ModMetadata ordinary=read(Path.of(args[1]),overrides);
        require("aqualumen_physics".equals(candidate.getId()),"Test must read the actual physics bridge");
        require(BathymetrySnapshot.acceptsPhysicsMetadata(candidate),
                "Actual candidate metadata must authorize the bridge identity without implementation-class access");
        require(!BathymetrySnapshot.acceptsPhysicsMetadata(ordinary),"The ordinary 0.2 bridge must not authorize candidate observation");
        require(!BathymetrySnapshot.acceptsPhysicsMetadata(null),"Unavailable metadata must be declined");
        System.out.println("PASS actual packaged Fabric metadata boundary: candidate accepted, ordinary/missing declined");
    }
    private static ModMetadata read(Path jar,Path overrides)throws Exception {
        try(ZipFile zip=new ZipFile(jar.toFile());var input=zip.getInputStream(zip.getEntry("fabric.mod.json"))) {
            return ModMetadataParser.parseMetadata(input,jar.getFileName().toString(),List.of(),
                    new VersionOverrides(),new DependencyOverrides(overrides),false);
        }
    }
    private static void require(boolean value,String message) {if(!value)throw new AssertionError(message);}
}
