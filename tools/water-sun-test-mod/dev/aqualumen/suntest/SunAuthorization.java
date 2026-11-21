package dev.aqualumen.suntest;

import dev.aqualumen.bench.BathymetrySnapshot;
import java.util.Properties;
import java.nio.file.Path;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.io.ByteArrayInputStream;
import java.util.function.IntSupplier;

/** TEST-only per-invocation permission; never an optical acceptance result. */
public final class SunAuthorization {
    private SunAuthorization() {}
    public record Input(boolean filesystemAuthorized, Properties configuration) {}
    /** Only real filesystem/Minecraft boundaries are replaceable in CPU tests. */
    public interface SystemBoundary {
        Input input() throws Exception;
        BathymetrySnapshot.Scope scope(Properties configuration) throws Exception;
    }
    public interface ScopeReader { BathymetrySnapshot.Scope read(Path game,Properties config) throws Exception; }
    public static SystemBoundary filesystem(Path game,ScopeReader reader) {
        return new SystemBoundary() {
            public Input input()throws Exception {
                Path canonical=game.toAbsolutePath().normalize();
                if(!canonical.equals(game)||!canonical.equals(game.toRealPath())||game.getFileName()==null
                        ||!"minecraft".equals(game.getFileName().toString())||game.getParent()==null
                        ||!"Aqualumen Lab".equals(game.getParent().getFileName().toString())
                        ||game.getParent().getParent()==null
                        ||!"instances".equals(game.getParent().getParent().getFileName().toString()))return new Input(false,null);
                Path directory=game.resolve("config");
                if(!canonicalDirectory(directory)||!boundedFile(directory.resolve("aqualumen-sun-test.enabled"))
                        ||!boundedFile(directory.resolve("aqualumen-benchmark.enabled")))return new Input(false,null);
                Properties config=properties(directory.resolve("aqualumen-benchmark.properties"));
                if(!dev.aqualumen.bench.ShoreRuntimeObserver.acceptsConfiguration(config))return new Input(false,null);
                Path packs=game.resolve("shaderpacks"),saves=game.resolve("saves"),world=saves.resolve("AqualumenNaturalV2");
                if(!canonicalDirectory(packs)||!canonicalDirectory(saves)||!canonicalDirectory(world))return new Input(false,null);
                Path archive=packs.resolve(config.getProperty("expected_pack"));
                if(!Files.isRegularFile(archive,LinkOption.NOFOLLOW_LINKS)||Files.size(archive)>16*1024*1024)return new Input(false,null);
                Properties marker=properties(world.resolve("aqualumen-world.properties"));
                boolean valid="2".equals(marker.getProperty("schema"))
                    &&"b22dbccb-2970-41e6-847f-f183b1ec923d".equals(marker.getProperty("world_id"))
                    &&"308060".equals(marker.getProperty("seed"))
                    &&"minecraft:noise/overworld".equals(marker.getProperty("generator"));
                return new Input(valid,config);
            }
            public BathymetrySnapshot.Scope scope(Properties configuration)throws Exception {return reader.read(game,configuration);}
        };
    }
    public static SystemBoundary runtime(Path game) {return filesystem(game,BathymetrySnapshot::inspectScope);}
    private static boolean canonicalDirectory(Path path)throws Exception {
        return Files.isDirectory(path,LinkOption.NOFOLLOW_LINKS)&&path.equals(path.toRealPath());
    }
    private static boolean boundedFile(Path path)throws Exception {
        return Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)&&Files.size(path)<=16384;
    }
    private static Properties properties(Path path)throws Exception {
        if(!boundedFile(path))throw new IllegalArgumentException();
        byte[] bytes;try(var input=Files.newInputStream(path,LinkOption.NOFOLLOW_LINKS)){bytes=input.readNBytes(16385);}
        if(bytes.length>16384)throw new IllegalArgumentException();
        Properties result=new Properties();result.load(new ByteArrayInputStream(bytes));return result;
    }
    public static IntSupplier supplier(SystemBoundary boundary) { return ()->value(boundary); }
    public static int value(SystemBoundary boundary) {
        try {
            Input input=boundary.input();
            if(input==null||!input.filesystemAuthorized())return 0;
            if(!dev.aqualumen.bench.ShoreRuntimeObserver.acceptsConfiguration(input.configuration()))return 0;
            return dev.aqualumen.bench.ShoreRuntimeObserver.acceptsScope(boundary.scope(input.configuration()))?1:0;
        } catch(Exception|LinkageError failure) { return 0; }
    }
}
