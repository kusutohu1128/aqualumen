#!/usr/bin/env bash
set -euo pipefail
cd /home/kusutohu/repos/aqualumen
prism_root=/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher
java_bin="$prism_root/java/java-runtime-delta/bin"
loader="$prism_root/libraries/net/fabricmc/fabric-loader/0.19.5/fabric-loader-0.19.5.jar"
mixin="$prism_root/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
task_classes=$(mktemp -d build/benchmark-classes.XXXXXX)
"$java_bin/javac" -proc:none -cp "$loader:$mixin" -d "$task_classes" tools/benchmark-mod/dev/aqualumen/bench/FrameMixin.java tools/benchmark-mod/dev/aqualumen/bench/Recorder.java
cp tools/benchmark-mod/fabric.mod.json tools/benchmark-mod/aqualumen-benchmark.mixins.json "$task_classes/"
"$java_bin/jar" --create --file build/aqualumen-benchmark-0.1.0.jar -C "$task_classes" .
printf '%s\n' 'Built build/aqualumen-benchmark-0.1.0.jar'
