package dev.aqualumen.suntest;

import dev.aqualumen.bench.BathymetrySnapshot;
import java.nio.file.Files;
import java.nio.file.Path;

/** Real temporary filesystem + explicitly synthetic external Minecraft scope. */
public final class SunFilesystemTest {
    private static final String ID="b22dbccb-2970-41e6-847f-f183b1ec923d";
    private static void expect(int expected,SunAuthorization.SystemBoundary b,String description) {
        int actual=SunAuthorization.value(b);if(actual!=expected)throw new AssertionError(description+": "+actual);
    }
    public static void main(String[] args)throws Exception {
        Path scratch=Files.createTempDirectory(Path.of(args[0]).toAbsolutePath().normalize(),"synthetic-files.");
        Path game=Files.createDirectories(scratch.resolve("instances/Aqualumen Lab/minecraft"));
        Path config=Files.createDirectory(game.resolve("config"));
        Files.writeString(config.resolve("aqualumen-sun-test.enabled"),"Explicit TEST-only opt-in\n");
        Files.writeString(config.resolve("aqualumen-benchmark.enabled"),"Synthetic TEST fixture\n");
        Files.writeString(config.resolve("aqualumen-benchmark.properties"),"schema=2\nworld=AqualumenNaturalV2\nworld_id="+ID+
            "\nexpected_pack=Aqualumen-ShoreProbe-world-sun-test.zip\nexpected_pack_sha256="+"a".repeat(64)+"\n");
        Files.createDirectory(game.resolve("shaderpacks"));Files.write(game.resolve("shaderpacks/Aqualumen-ShoreProbe-world-sun-test.zip"),new byte[]{1});
        Path world=Files.createDirectories(game.resolve("saves/AqualumenNaturalV2"));
        Files.writeString(world.resolve("aqualumen-world.properties"),"schema=2\nworld_id="+ID+"\nseed=308060\ngenerator=minecraft:noise/overworld\n");
        SunAuthorization.SystemBoundary b=SunAuthorization.filesystem(game,(g,c)->
            new BathymetrySnapshot.Scope(true,true,false,1,true,"AqualumenNaturalV2",ID,308060,"minecraft:overworld",true,true));
        expect(1,b,"approved real filesystem and synthetic external live scope");
        Path sun=config.resolve("aqualumen-sun-test.enabled"),benchmark=config.resolve("aqualumen-benchmark.enabled");
        for(Path marker:new Path[]{sun,benchmark}) {
            Path held=marker.resolveSibling(marker.getFileName()+".held");Files.move(marker,held);
            expect(0,b,"absent "+marker.getFileName());
            Files.createSymbolicLink(marker,held);expect(0,b,"symlinked "+marker.getFileName());
            Files.move(marker,marker.resolveSibling(marker.getFileName()+".rejected-link"));Files.move(held,marker);
            Files.writeString(marker,"x".repeat(16385));expect(0,b,"oversized "+marker.getFileName());
            Files.writeString(marker,"Synthetic restored opt-in\n");expect(1,b,"restored marker");
        }
        Path configuration=config.resolve("aqualumen-benchmark.properties");String original=Files.readString(configuration);
        Files.writeString(configuration,"x".repeat(16385));expect(0,b,"oversized benchmark configuration");
        Files.writeString(configuration,original.replace("schema=2","schema=1"));expect(0,b,"wrong configuration schema");
        Files.writeString(configuration,original);expect(1,b,"config reload reads new bytes");
        Path marker=world.resolve("aqualumen-world.properties");String worldMarker=Files.readString(marker);
        Files.writeString(marker,worldMarker.replace("seed=308060","seed=1"));expect(0,b,"wrong saved-world marker");
        Files.writeString(marker,worldMarker);expect(1,b,"restored saved-world marker");
        Path alias=scratch.resolve("alias-game");Files.createSymbolicLink(alias,game);
        expect(0,SunAuthorization.filesystem(alias,(g,c)->b.scope(c)),"game path alias rejected");
        System.out.println("PASS real synthetic filesystem: approved Lab, both missing/symlink/oversized markers, bounded config, reload, world marker, path alias");
    }
}
