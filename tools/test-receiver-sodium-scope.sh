#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
prism="${AQUALUMEN_PRISM_ROOT:-/home/kusutohu/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher}"
java_bin="$prism/java/java-runtime-delta/bin"
classpath="$prism/instances/Aqualumen Lab/minecraft/mods/iris-fabric-1.8.8+mc1.21.1.jar:$prism/instances/Aqualumen Lab/minecraft/mods/sodium-fabric-0.6.9+mc1.21.1.jar"
classes=$(mktemp -d build/receiver-sodium-scope-test.XXXXXX)
"$java_bin/javac" -proc:none -cp "$classpath" -d "$classes" physics-mod/dev/aqualumen/physics/ReceiverField.java physics-mod/dev/aqualumen/physics/ReceiverVertex.java physics-mod/dev/aqualumen/physics/ReceiverVertexShader.java physics-mod/dev/aqualumen/physics/ReceiverRadianceVolume.java physics-mod/dev/aqualumen/physics/ReceiverMemberCache.java physics-mod/dev/aqualumen/physics/ReceiverSodiumScope.java physics-mod/dev/aqualumen/physics/ReceiverSodiumIntake.java physics-mod/test/dev/aqualumen/physics/ReceiverSodiumScopeTest.java
"$java_bin/java" -cp "$classes:$classpath" dev.aqualumen.physics.ReceiverSodiumScopeTest
