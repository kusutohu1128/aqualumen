# Aqualumen

水と太陽光を中心にした、Minecraft Java版の自作Irisシェーダーパックです。
初期版 `0.1.0`。完成した流体シミュレーターではなく、物理モデルを用いた描画の試作です。

## 基準環境

- NVIDIA RTX 3080 Ti / VRAM 12 GB
- 2560×1440、描画距離12チャンク、シミュレーション距離6チャンク
- Minecraft 1.21.1 / Java 21 / Fabric Loader 0.19.5
- Iris 1.8.8 / Sodium 0.6.9（正式版を固定）
- 標準の `BALANCED` プロファイル
- 目標: 60 FPS / 16.67 ms。測定結果と目標は区別します。

## 実装

水面は深水波の分散関係 `ω²=gk` を使う6成分の波で動きます。波の勾配から法線を求め、視距離に応じて細かな波を弱めます。FFTや水量を保存する流体ソルバーは未実装です。風の設定は現在、波の進む速度を変えます。

水面の反射率は誘電体のFresnel式、屈折方向はSnellの法則を使います。水中からの全反射も扱います。水中の光の減衰はRGB別の指数関数で計算します。濁りの散乱は簡略化した近似です。

水面の同じ波から屈折光の着地点の微分を求め、水底の集光模様（コースティクス）を近似します。受光面を水平とみなし、発散を抑えるため明るさを制限しています。光子追跡や水中の遮蔽物の正確な処理はありません。

空は球状大気のRayleigh/Mie単一散乱を積分して、毎フレーム256×128のLUTに保存します。多重散乱と夜間光は明示的な近似です。太陽の円盤、地形の直接光、水面のハイライトは同じ太陽方向と大気透過率を使います。

反射は画面内の深度を探索し、見つからない場合は空を使います。画面外の建物や地形は反射できません。薄い地形での反射・屈折の欠落、透明ブロックを重ねた場合の描画制限、波の境界や時間方向のちらつきは今後の検証対象です。

影は2048pxのシャドウマップと8サンプルのフィルター、光芒は10ステップの近似です。HDRの色をトーンマッピングし、最後に軽い空間フィルターを適用します。TAA、実際の船の航跡、岸で砕ける波、ブロック間の流体物理は未実装です。

## このPCで使う

Prism Launcherに専用インスタンス **Aqualumen Lab** を作成しました。既存のModパックとは独立しています。シェーダーは有効な状態で配置されています。

配布用ZIPは `dist/Aqualumen-0.1.0.zip` です。別のIris環境では、そのインスタンスの `shaderpacks` にZIPのまま置いてIrisの設定画面から選択してください。

```bash
cd /home/kusutohu/repos/aqualumen
python3 tools/build.py
```

画質設定は `軽量 / 標準 / 高画質` の3段階です。60 FPSを優先する場合は標準から開始し、実際のプレイ環境で下回る場合は軽量を選んでください。

## 検証

```bash
cd /home/kusutohu/repos/aqualumen
make check
```

`make check` はEGLのOpenGL互換コンテキスト上で11組のプログラムをコンパイル・リンクし、水の反射・全反射・減衰をGPUの実出力で確認します。出力の `Renderer` を確認してください。llvmpipeでの結果をNVIDIAでの結果として扱ってはいけません。これはMinecraftのFPS測定ではありません。

Minecraft内の測定には開発専用Modを用意しています。専用インスタンスかつ `config/aqualumen-benchmark.enabled` が存在する場合に限り、ローカルの統合サーバーで測定用の地形とカメラを設定します。通常利用時は無効にしてあります。

```bash
bash tools/build-benchmark-mod.sh
```

各場面は15秒の待機後に30秒測定します。記録対象は描画ループの連続フレーム間隔で、GPU単体の時間ではありません。平均FPS、遅い1%のフレーム時間の平均から計算したFPS、99パーセンタイル、最も長いフレーム、16.67ms超の回数を保存します。

測定場面は昼の水面、岸と影、夕方の水面、水中、視点の回転です。用意した小さな人工ワールドでの結果に限定されます。大規模な建築やModパック、チャンク生成を含むプレイ全体の60 FPS保証にはなりません。生のフレームCSVを含め、最終結果は `reports/` に保存します。

2026-10-01の実機測定では、5場面の平均507〜681 FPS、遅い1%のFPSは261〜318でした。全場面を通して最長のフレームは7.96 msで、測定区間中に16.67 msを超えたフレームはありません。[場面別の結果と測定条件](reports/2026-10-01/RESULTS.md)を参照してください。

最初のオフライン起動ではFabricのマッピングJARが不足していました。公式配布のSHA-256を確認して配置し、再起動後のIris/Sodium読み込みとシェーダー描画を確認しています。`tools/download-mods.mjs` にもマッピングの取得・検証を含めました。

## 実装の参考

- [Irisのパイプラインとプログラム](https://shaders.properties/current/reference/programs/overview/)
- [Irisの深度バッファ](https://shaders.properties/current/reference/buffers/depthtex/)
- [Irisの色バッファと描画中の制約](https://shaders.properties/current/reference/buffers/colortex/)
- [NVIDIA: 波の物理モデル](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)
- [NVIDIA: 水底の集光の原理](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)
- [Bruneton: 大気散乱のモデルと実装](https://ebruneton.github.io/precomputed_atmospheric_scattering/)

既存シェーダーパックの描画コードやアセットは使用していません。
