#!/usr/bin/env bash
set -euo pipefail
src=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$src/../../../.." && pwd)
work=$(mktemp -d "$root/build/private-clock.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
prism="$HOME/.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher"
java="$prism/java/java-runtime-delta/bin"
mixin="$prism/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"
gl="$prism/libraries/org/lwjgl/lwjgl-opengl/3.3.3/lwjgl-opengl-3.3.3.jar"
"$java/javac" --release 21 -proc:none -cp "$mixin:$gl" -d "$work" "$src/DispatchClock.java"
cat >"$work/fabric.mod.json" <<'META'
{"schemaVersion":1,"id":"aqualumen_private_clock","version":"0.1.0","name":"Isolated cave GPU clock","environment":"client","mixins":["clock.mixins.json"],"depends":{"minecraft":"1.21.1","iris":"1.8.8"}}
META
cat >"$work/clock.mixins.json" <<'META'
{"required":true,"minVersion":"0.8","package":"dev.aqualumen.privateclock.mixin","compatibilityLevel":"JAVA_21","client":["DispatchClock"],"injectors":{"defaultRequire":1}}
META
"$java/jar" --create --date=2026-11-21T00:00:00Z --file "$work.jar" -C "$work" .
mv -n "$work.jar" "$root/build/aqualumen-private-gpu-clock.jar"
