# 実行コマンド（リポジトリ直下で実行）

親の `build/glcheck` と競合しないよう、私用バイナリ `build/claude-lava-qa/glcheck-lava2` を使った。

```sh
# ビルド（Makefile の build/glcheck と同じフラグ、出力先だけ私用）
g++ -std=c++17 -O2 -Wall -Wextra tools/glcheck.cpp -o build/claude-lava-qa/glcheck-lava2 -lepoxy -lEGL

# 1.8.0 基準パック（release/shaders と同一内容）の展開先
unzip -oq dist/Aqualumen-1.8.0.zip -d build/claude-lava-qa/base180

# 溶岩専用プローブ（NVIDIA surfaceless EGL、描画ロックをジョブごとに取得）
flock -w 3000 /tmp/aql-render21-1000.lock build/claude-lava-qa/glcheck-lava2 \
  build/lava-v190-src/shaders --lava-light-probe build/claude-lava-qa/base180/shaders build/claude-lava-qa/lava-nvidia.json

# 既存回帰（候補と release の両方、プローブ別）
for m in local-light entity-light bounce-light door-light leaf-light rain-film; do
  flock -w 3000 /tmp/aql-render21-1000.lock build/claude-lava-qa/glcheck-lava2 build/lava-v190-src/shaders --$m-probe
  flock -w 3000 /tmp/aql-render21-1000.lock build/claude-lava-qa/glcheck-lava2 release/shaders --$m-probe
done
# 通常配布用の全回帰（溶岩プローブは最後に実行される）
flock -w 3000 /tmp/aql-render21-1000.lock build/claude-lava-qa/glcheck-lava2 build/lava-v190-src/shaders --play-release
flock -w 3000 /tmp/aql-render21-1000.lock build/claude-lava-qa/glcheck-lava2 release/shaders --play-release

# 独立クロスチェック（Mesa llvmpipe、GPU とロックを使わない）
__EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json LIBGL_ALWAYS_SOFTWARE=1 \
  build/claude-lava-qa/glcheck-lava2 build/lava-v190-src/shaders --lava-light-probe \
  build/claude-lava-qa/base180/shaders build/claude-lava-qa/lava-mesa.json

# 集約（GPU を使わない）
python3 reports/2026-11-21-lava-light/gpu-v190/assemble.py
```

まとめて実行するスクリプト: `build/claude-lava-qa/run-nvidia.sh`（ジョブごとにロック取得）。

Make ターゲット（親が使う場合）:

```sh
make check-lava LAVA_SHADERS=build/lava-v190-src/shaders LAVA_BASELINE=build/claude-lava-qa/base180/shaders
```
