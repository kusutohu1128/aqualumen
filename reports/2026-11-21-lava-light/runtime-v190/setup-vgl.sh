#!/bin/sh
# Reproducible user-local VirtualGL 3.1.5 (public GitHub release .deb), extracted into a NEW private dir; no sudo/install.
# Usage: ./setup-vgl.sh  -> prints the dir and records it in vgl-dir.txt next to this script.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dir=$(mktemp -d /tmp/aql-v190-vgl-XXXXXX)
mkdir "$dir/dl" "$dir/x"
curl -sS --max-time 120 -L -o "$dir/dl/virtualgl.deb" https://github.com/VirtualGL/virtualgl/releases/download/3.1.5/virtualgl_3.1.5_amd64.deb
test "$(sha256sum "$dir/dl/virtualgl.deb" | cut -d' ' -f1)" = df3f7788ce41b182a47c0d298e5cd6d2d63579522cb41825970b7726e825485e
dpkg-deb -x "$dir/dl/virtualgl.deb" "$dir/x"
printf '%s\n' "$dir" > "$here/vgl-dir.txt"
echo "$dir"
