# コントリビューション

Aqualumen への貢献を歓迎します。バグ報告（スクリーンショット付き）、シェーダーの修正、ドキュメントの改善が対象です。

## 動作環境

- Minecraft Java 1.21.1
- Iris 1.8.8 / Sodium 0.6.9
- Java 21

## 開発の流れ

1. 安定版 1.8.0 のシェーダーは `release/shaders/` を編集します。実験版・プレビューは `release/<variant>/` の重ねるレイヤーで、`tools/build.py` のフラグが積層します。
2. `python3 tools/build.py --release` で `dist/Aqualumen-1.8.0.zip` をビルドします。`python3 tools/build.py --help` に実験版・プレビュー用のフラグ一覧があります。
3. `make check` で `release/shaders` の描画プログラムのコンパイル・リンクと各種GPUプローブ、雨よけプローブを実行します。EGL と libepoxy の開発ファイルが必要です。機能ごとの検査は `make check-lava`、`make check-canopy` などです。
4. GitHub Actions の CI は Mesa llvmpipe（ソフトウェアレンダラー）で `make check` を実行します。**ソフトウェアの結果は NVIDIA の結果ではありません。** CIではNVIDIA実機でのみ検証している2つのプローブ（前景の影と霞、地形の日照スナップショット）と1件のコンパイル厳格性チェックをスキップするため、CIが緑でも実機NVIDIAでの実行の代わりにはなりません。自分の環境で検査したら、GLレンダラーとGPU名を必ず報告してください。

## 報告・記録のルール

- 既存シェーダーパックのコードや有料アセットのコピーは不可です。アルゴリズムの参考文献は README の参考文献に記載してください。
- レポートでは、解析的・近似的な描画、実際の流体シミュレーション、GPUハーネスの計測時間、Minecraftのフレーム時間を区別してください。
- フレーム時間はGPU名・解像度・チャンク数を添えて正直に報告してください。

## プルリクエスト

- 変更は目的ごとに小さく保ってください。
- キャプチャ画像や動画などの大きなメディアはPRに含めず、リンクで参照してください。
- PR には `make check` の結果と使用したGLレンダラー、ゲーム内での確認（GPU・解像度・チャンク数）、追加した参考文献を書いてください。

## ライセンス

このプロジェクトは MIT ライセンスです。貢献は MIT ライセンスの下で提供されるものとします。

---

# Contributing (English summary)

Contributions are welcome: bug reports with screenshots, shader fixes, and docs. Requires Minecraft Java 1.21.1, Iris 1.8.8, Sodium 0.6.9, Java 21.

Edit `release/shaders/` for the stable pack or `release/<variant>/` overlay layers, build with `python3 tools/build.py --release`, and verify with `make check` (needs EGL + libepoxy dev files). GitHub CI runs `make check` on Mesa llvmpipe — software results are not NVIDIA results, and CI skips the two NVIDIA-only probes (foreground shadow/haze, terrain Sun snapshot) and one compile-strictness check, so a green CI run is not a substitute for an NVIDIA run. Always report your GL renderer and GPU.

Do not copy shader-pack code or purchased assets; cite algorithm references in the README references. Distinguish approximate rendering, actual simulation, GPU-harness timings, and Minecraft frame times; report frame timings honestly with GPU, resolution, and chunk count. Keep PRs focused, link large media instead of committing it, and submit contributions under the MIT license.
