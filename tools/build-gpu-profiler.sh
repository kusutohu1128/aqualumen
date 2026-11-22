#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
out=build/gpu-profiler
src=tools/gpu-profiler-mod
prism_root="${AQUALUMEN_PRISM_ROOT:-$HOME/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
game="$prism_root/instances/Aqualumen Lab/minecraft"
lib="$prism_root/libraries"
java="$prism_root/java/java-runtime-delta/bin"
iris="$game/mods/iris-fabric-1.8.8+mc1.21.1.jar"
sodium="$game/mods/sodium-fabric-0.6.9+mc1.21.1.jar"
mc="$game/.fabric/remappedJars/minecraft-1.21.1-0.19.5/client-intermediary.jar"
mixin="$lib/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
loader="$lib/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
gl="$lib/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
pin() { printf '%s  %s\n' "$1" "$2" | sha256sum -c -; }
pin b5ad39a6cb113ca0a1765f06689f9f4b29ccd0c81247de90b06c42f5da1092f5 "$iris"
pin 411c4c03167066f0e2e61ba17793b4be13ddd73de5b677c6d402f1d8f4262ac2 "$sodium"
pin ffcab71074c28fac8521c30eb6e11f10333f76f3e173f7401aef5cfb26054563 "$mc"
pin 93044e4dd46de5d8136701292f05e868da096d2c9fddb4793e4fdbcc63efc695 "$loader"
pin 1f0ae44db7295f8626f33b1dc0ad7f043d8954a8d6847247875fcc5dfcecc934 "$mixin"
pin 5062da750e5f7ec89e27e8b67b7d40fa8c4b16890159e35f828116ce6c8eca1e "$gl"
mkdir -p "$out"
python3 -B reports/2026-11-21-animal-light/timing/build.py "$out/frame-sample.jar"
work=$(mktemp -d "$out/compile.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
cp="$iris:$sodium:$mc:$mixin:$loader:$gl:$out/frame-sample.jar"
for artifact in asm asm-tree; do cp+=":$lib/org/ow2/asm/$artifact/9.10.1/$artifact-9.10.1.jar"; done
mkdir "$work/classes"
"$java/javac" --release 21 -proc:none -cp "$cp" -d "$work/classes" "$src"/*.java
"$java/java" -ea -cp "$work/classes" dev.aqualumen.profiler.QueryPolicyTest
"$java/java" -ea -cp "$work/classes:$cp" dev.aqualumen.profiler.AttributionTest
rm "$work/classes/dev/aqualumen/profiler/"*Test*.class
"$java/java" -cp "$work/classes:$cp" dev.aqualumen.profiler.Hooks | tee "$work/injections.txt"
cp "$src"/*.json LICENSE "$work/classes/"
"$java/jar" --create --date=2026-11-21T00:00:00Z --file "$work/profiler.jar" -C "$work/classes" .
mv "$work/profiler.jar" "$out/gpu-profiler.jar"
mv "$work/injections.txt" "$out/injections.txt"
sha256sum "$out"/{gpu-profiler,frame-sample}.jar
