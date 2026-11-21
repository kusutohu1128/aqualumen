#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism_root='/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher'
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
benchmark='build/aqualumen-benchmark-0.3.9-projection-guards.jar'
final='build/aqualumen-atlas-final-probe-0.1.3.jar'
output='build/aqualumen-atlas-joint-probe-0.1.3.jar'
[[ ! -e "$output" && ! -L "$output" ]] || { printf '%s\n' 'Refusing existing output'; exit 1; }
[[ $(sha256sum "$benchmark" | cut -d' ' -f1) == ef303d4b53a1299e64e562e81cf3ed70dfaffe96d99f5b8cbb58ff864cfd7b29 ]]
[[ $(sha256sum "$final" | cut -d' ' -f1) == 6ce3747695e5d5e973f2e5c8aa9f1b0414a05abd95ab26ce203a5ad7f54091f0 ]]
classes=$(mktemp -d build/atlas-joint-classes.XXXXXX)
tests=$(mktemp -d build/atlas-joint-tests.XXXXXX)
"$java_bin/javac" -proc:none -cp "$loader:$mixin:$benchmark:$final" -d "$classes" tools/atlas-joint-probe/dev/aqualumen/atlasjoint/*.java tools/atlas-joint-probe/dev/aqualumen/atlasjoint/mixin/*.java
"$java_bin/javac" -proc:none -cp "$classes" -d "$tests" tools/atlas-joint-probe/test/dev/aqualumen/atlasjoint/OutputSnapshotTest.java
"$java_bin/java" -cp "$tests:$classes" dev.aqualumen.atlasjoint.OutputSnapshotTest
cp tools/atlas-joint-probe/*.json "$classes/"
"$java_bin/jar" --create --file "$output" -C "$classes" .
sha256sum "$output"
