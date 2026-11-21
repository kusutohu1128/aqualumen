package dev.aqualumen.compiler;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.lwjgl.opengl.GL11;

public final class LightingCompiler {
    private static final Pattern VERSION = Pattern.compile("(?m)^[ \\t]*#version[^\\r\\n]*\\r?\\n");
    private static final String DIRECTIVE = "#pragma optionNV(inline 128)";
    private static final AtomicBoolean irisLogged = new AtomicBoolean();
    private static final AtomicBoolean minecraftLogged = new AtomicBoolean();

    private LightingCompiler() {}

    public static boolean isAreaLighting(String source) {
        return source.contains("aqualumenAreaSourceLighting") && source.contains("aqualumenLightField");
    }

    public static String prepare(String source, boolean minecraft) {
        if (!isAreaLighting(source) || source.contains("local_size_x") || source.contains(DIRECTIVE)
                || !"NVIDIA Corporation".equals(GL11.glGetString(GL11.GL_VENDOR))) {
            return source;
        }
        Matcher version = VERSION.matcher(source);
        if (!version.find()) return source;
        if ((minecraft ? minecraftLogged : irisLogged).compareAndSet(false, true)) {
            System.getLogger("Aqualumen Lighting").log(System.Logger.Level.INFO,
                    "Compiling Aqualumen area lighting with NVIDIA function calls via "
                            + (minecraft ? "Minecraft shader programs" : "Iris or Sodium shader programs"));
        }
        return source.substring(0, version.end()) + DIRECTIVE + "\n" + source.substring(version.end());
    }
}
