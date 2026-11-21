#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root='/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher'
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
benchmark='build/aqualumen-benchmark-0.3.9-projection-guards.jar'
output='build/aqualumen-atlas-final-probe-0.1.3.jar'
iris="$prism_root/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar"
[[ ! -e "$output" && ! -L "$output" ]] || { printf '%s\n' 'Refusing existing output'; exit 1; }
for dependency in "$loader" "$mixin" "$benchmark"; do
    [[ -f "$dependency" && ! -L "$dependency" ]] || exit 1
done
benchmark_digest=$(sha256sum "$benchmark")
[[ "${benchmark_digest%% *}" == 'ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29' ]] || exit 1
classes=$(mktemp -d build/atlas-final-classes.XXXXXX)
tests=$(mktemp -d build/atlas-final-tests.XXXXXX)
"$java_bin/javac" -proc:none -cp "$loader:$mixin:$benchmark:$iris" -d "$classes" \
    tools/atlas-final-probe/dev/aqualumen/atlas/FinalSnapshot.java \
    tools/atlas-final-probe/dev/aqualumen/atlas/FinalObserver.java \
    tools/atlas-final-probe/dev/aqualumen/atlas/mixin/FinalMixin.java \
    tools/atlas-final-probe/dev/aqualumen/atlas/mixin/LinkMixin.java
"$java_bin/javac" -proc:none -cp "$classes" -d "$tests" \
    tools/atlas-final-probe/test/dev/aqualumen/atlas/FinalSnapshotTest.java
"$java_bin/java" -cp "$tests:$classes" dev.aqualumen.atlas.FinalSnapshotTest
cp tools/atlas-final-probe/fabric.mod.json tools/atlas-final-probe/aqualumen-atlas-final.mixins.json "$classes/"
"$java_bin/jar" --create --file "$output" -C "$classes" .
sha256sum "$output"
