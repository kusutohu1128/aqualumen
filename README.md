# Aqualumen

Minecraft Java 1.21.1 用の光と水の Iris シェーダーです。松明やランタンの光が葉や幹を透して届き、手に持って歩くと照らす位置と影が一緒に移ります。雨に濡れた面や水面の屈折、流れる雲が直射日光を遮る大気まで、近くの光をまとめて計算します。

## English

Aqualumen is an Iris shader pack for Minecraft Java 1.21.1 focused on light and water: local lights that pass through leaves, carried-light shadows that move with you, rain-wet surfaces, refractive water, and a scattering atmosphere. Requires Fabric, Iris 1.8.8, Sodium 0.6.9, and Java 21. Download the shader, world saves, and mods from [Releases](https://github.com/kusutohu1128/aqualumen/releases). Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under MIT.

## 導入

- 対応環境は Minecraft 1.21.1 / Java 21 / Fabric / Iris 1.8.8 / Sodium 0.6.9 です。
- [シェーダー 1.8.0](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/Aqualumen-1.8.0.zip) を `shaderpacks/` に、[接触波紋用Mod 0.2.0](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/aqualumen-physics-0.2.0.jar) を `mods/` に入れます。Modは接触波紋とディメンション判定に必要で、なくても光学と風波は使えます。配布物はすべて [Releases](https://github.com/kusutohu1128/aqualumen/releases) にあります。
- 標準設定は `BALANCED` です。RTX 3080 Ti・2560×1440・描画12チャンクで検証しています。以前の水の見え方に戻したいときは、Labに残してある `Aqualumen-0.6.0.zip` を選べます。

## このPCで遊ぶ

Prism Launcher で **Aqualumen Lab** を起動し、Esc → 設定 → ビデオ設定 → シェーダーパックで `Aqualumen-1.8.0.zip` を選んでください。「シングルプレイ」から下のワールドを開くと、雨・木陰・雪・灯りのある場面をそのまま歩けます。水に入って見上げると空が丸く収まり、その縁が波に合わせて動きます。水面で全反射する角度では水中の景色が映ります。通常プレイには計測用Modもワールドの切り替えも不要です。

| ワールド | 始まる場所と見どころ | 操作 | ZIP |
|---|---|---|---|
| Aqualumen Rain Walk | 雨の降る夕方、ランタンを吊った軒先に立ち、北の道を進むと坑道の先に池があります。 | 1番は空の手、2番は松明、3番と4番は通常と魂のランタン | [遊べる雨の散歩道](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/Aqualumen-Rain-Walk.zip) · [雨と晴れの木陰で松明を付け外しした比較](reports/2026-11-21-rain-eaves/journey/run-7/oak-torch.jpg) · [松明と魂のランタンを片方ずつ消す](reports/2026-11-21-rain-eaves/journey/run-8/two-lights.jpg) · [坑道と池を巡る約30秒の映像](reports/2026-11-21-rain-eaves/journey/run-7/walk-highlights.mp4) |
| Aqualumen Woodland | 自然生成のオークの西側に立ち、木の西に水辺、東の斜面に石の洞穴があります。 | 1番は空の手、2番は松明、3番は魂の松明 | [遊べる森](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/Aqualumen-Woodland.zip) · [サバイバルで松明を置いた場面](reports/2026-11-21-leaf-light/play/release-roundtrip/woodland-lights.jpg) · [夜の岸から見た水面](reports/2026-11-21-leaf-light/play/slope-return/water-surface.png) |
| Aqualumen Snow Village | 夕方、雪の降る村の小道から始まり、正面のトウヒの家の中に入れます。 | 空の手で扉を開け、3番の魂の松明を持つと窓や床に青い光が届きます | [遊べる雪村](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/Aqualumen-Snow-Village.zip) · [通常プレイで家の扉を開けて中に入る](reports/2026-11-21-settlement-light/playable/village-house.jpg) |
| Aqualumen Lantern House | 夕暮れの並木道に立ち、道の先の家の二部屋の間の扉を開けられます。 | 9番の空きスロットで幹の松明を外し1番で置き直す。手を空けて扉を右クリック | [遊べるワールド](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/Aqualumen-Lantern-House.zip) · [玄関までの道](reports/2026-11-21-door-light/playable/smoke/01-spawn.png) · [同じ家で二灯と扉を操作した実画像](reports/2026-11-21-door-light/sky-control/ordinary-house.jpg) · [扉を開閉した動画](reports/2026-11-21-door-light/interaction/shipped/lever-door.mp4) |
| Aqualumen Lava Cavern（プレビュー） | 天然洞窟で、岩棚の上から魂の松明とバケツを使えます。 | 魂の松明とバケツ | [体験用セーブ](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/Aqualumen-Lava-Cavern.zip) · [溶岩と魂の松明の実画面](reports/2026-11-21-lava-light/cavern/ordered-survival/cavern-light.jpg) |

ワールドのZIPは展開して、中のワールドフォルダを `saves/` に入れます。

## 主な機能

- **水面**: 波の傾きから屈折・Fresnel反射・全反射を計算し、カメラから隠れた水底の材質と照明を記録して屈折光線と交差させます。浅瀬の減衰・濡れた砂・集光まで、解析的な表現です。[検証記録](reports/2026-11-20-shore-light/README.md)
- **大気と体積雲**: 球状大気のRayleigh/Mie単一散乱をLUTに保存し、曲面の体積層で雲の厚みと遮光を近似します。多重散乱や地面の環境光は近似です。[開発記録](docs/HISTORY.md)
- **設置光源**: 松明・ランタン・焚き火・シーランタンの発光状態から光源を取得し、逆二乗減衰で面ごとに照度を加算します。8ブロック四方の各立方体で最大12灯を選び、色付きガラスの透過色と炎の色は演出用の近似です。[検証記録](reports/2026-11-20-local-light/README.md)
- **葉を透過する光**: 可視面の位置から葉の厚みと光源までの経路を求め、幹・石壁・扉による遮蔽を考慮します。連なった樹冠の内側は平均的な減衰で近似しています。[検証記録](reports/2026-11-21-leaf-light/README.md)
- **雨と濡れた面**: 雨粒の散乱とGGXの微小面モデルで濡れた面の質感を分け、乾いた軒下には材質本来の質感を残します。[検証記録](reports/2026-11-21-rain-eaves/README.md)
- **扉を通る光**: 扉のテクスチャと厚さから各隙間を見通せる割合を求め、ランタンの光が壁に落ちる縁をぼかします。[検証記録](reports/2026-11-21-door-light/README.md)
- **手持ち光源と露出順応**: 両手に持った光源が岩に同時に届き、露出は目の前の面に実際に届いた光に応じて変化します。[検証記録](reports/2026-11-21-carried-light/README.md)
- **一回反射の間接光**: 柱の陰で直接光が見えない面にも、近くの不透明な面での拡散反射を一回まで追って光を届けます。[検証記録](reports/2026-11-21-indirect-light/README.md)
- **生き物の影**: 牛の頭・胴・脚が局所光を遮り、動くと影も壁の上を移動します。[検証記録](reports/2026-11-21-mob-light/README.md)
- **接触波紋**: 水に触れた位置と移動からGPU上の高さ/速度場を更新する、局所的な線形波高シミュレーションです。Minecraftの水量・流れ・浮力を置き換えるNavier–Stokesソルバーではありません。[計算の記録](docs/HISTORY.md)

機能の詳細は [docs/FEATURES.md](docs/FEATURES.md) にまとめています。

## 実験版と 1.9.0 プレビュー

通常版とは別にビルドして試す実験版と 1.9.0 プレビューです。溶岩などの面光源プレビューでは、[照明コンパイラ 0.3.0](https://github.com/kusutohu1128/aqualumen/releases/download/v1.8.0/aqualumen-lighting-compiler-0.3.0.jar) を `mods/` に置いてMinecraftを再起動してから、Irisでプレビューを選びます。プレビュー14ではこのModは任意で、置くと最初のコンパイルが短くなります。プレビュー3〜13とそれらを土台にした実験版では引き続き必要です。このPCの **Aqualumen Lab** で選べる最新の任意パックはプレビュー10です。詳しい経緯は [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) にあります。

| 版 | 内容 | ビルド | ZIP | 記録 |
|---|---|---|---|---|
| Glass-View-Pass | 近くの色付き板ガラス越しに景色を見る。重ねた板の色と厚みで向こうから届く光が変わる。 | `python3 tools/build.py --glass-view-pass` | [Aqualumen-Glass-View-Pass.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Glass-View-Pass.zip) | [検証記録](reports/2026-11-23-camera-glass/README.md) |
| Sunlit-Panes | 色付き板ガラスを通った松明や日光が、奥の壁や床に色を落とす。 | `python3 tools/build.py --sunlit-panes` | [Aqualumen-Sunlit-Panes.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Sunlit-Panes.zip) | [検証記録](reports/2026-11-23-stained-panes/README.md) |
| Window-Tiles | 光が届く画面領域を調べ、必要な場所を窓用のシェーダーで描く。窓に背を向けても床や壁が着色される。 | `python3 tools/build.py --window-tiles` | [Aqualumen-Window-Tiles.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Window-Tiles.zip) | [検証記録](reports/2026-11-23-screen-windows/README.md) |
| Window-Routing | 松明が板ガラスを照らすときだけ窓用の描画に切り替える。 | `python3 tools/build.py --window-routing` | [Aqualumen-Window-Routing.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Window-Routing.zip) | [検証記録](reports/2026-11-23-window-routing/README.md) |
| Diffuse-Display | 明るさの中間域を調整し、岩壁・松明の炎・暗い面を同じ視点で比較できる。 | `python3 tools/build.py --diffuse-display` | [Aqualumen-Diffuse-Display.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Diffuse-Display.zip) | [検証記録](reports/2026-11-23-stone-display/README.md) |
| Torch-Shadow-Rows | 地面から松明の炎までの間で、光を遮りうる範囲だけを探す。 | `python3 tools/build.py --torch-shadow-rows` | [Aqualumen-Torch-Shadow-Rows.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Torch-Shadow-Rows.zip) | [検証記録](reports/2026-11-23-torch-brick-scan/README.md) |
| Torch-Shadow-Geometry | 幹や段差のどの部分が火を隠すかを調べ、複数ブロックが作る半影を試せる画質優先版。 | `python3 tools/build.py --torch-shadow-geometry` | [Aqualumen-Torch-Shadow-Geometry.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Torch-Shadow-Geometry.zip) | [検証記録](reports/2026-11-23-torch-shadow-integral/README.md) |
| Torch-Shadow-Contours | 火がブロックの角をかすめるときの遮光面積を安定させ、幹と段差の影を軽く計算する。 | `python3 tools/build.py --torch-shadow-contours` | [Aqualumen-Torch-Shadow-Contours.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Torch-Shadow-Contours.zip) | [検証記録](reports/2026-11-23-torch-shadow-integral/README.md) |
| Placed-Torch-Shadows | 幹と段差が作る松明の影を試せる。幹の横に土を置くと壁の影が変わる。 | `python3 tools/build.py --placed-shadow-union-study` | [Aqualumen-Placed-Torch-Shadows.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Placed-Torch-Shadows.zip) | [検証記録](reports/2026-11-23-mixed-occluders/README.md) |
| Placed-Penumbra-Animal-Study | 設置松明の半影。木陰の地面に光が届き幹の奥に柔らかな縁の影が残り、牛が横切ると体が影を落とす。 | `python3 tools/build.py --placed-penumbra-animal-study` | [Aqualumen-Placed-Penumbra-Animal-Study.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Placed-Penumbra-Animal-Study.zip) | [検証記録](reports/2026-11-23-placed-penumbra/README.md) |
| Torch-Cell-Study | 松明の光が遮られずに届く地形をワールド座標ごとに覚えるキャッシュ実験版。 | `python3 reports/2026-11-23-torch-open-volume/cell_pack.py --export` | [Aqualumen-Torch-Cell-Study.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Torch-Cell-Study.zip) | [検証記録](reports/2026-11-23-torch-open-volume/README.md) |
| Wet-Plane-Study | 水平な丸石を照らしたランタンの反射に現れる傾きを補正する試作。プレビュー13を土台にした独立したZIP。 | `python3 tools/build.py --wet-plane-study` | [Aqualumen-Wet-Plane-Study.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Wet-Plane-Study.zip) | [検証記録](reports/2026-11-23-wet-receiver/README.md) |
| 1.9.0 プレビュー14 | 照明コンパイラなしで動く溶岩面光源。水面・生き物・手持ちの溶岩光は従来のブロック光。 | `python3 tools/build.py --compile-budget-preview` | [Aqualumen-1.9.0-preview.14.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.14.zip) | [検証記録](reports/2026-11-24-mod-free/README.md) |
| 1.9.0 プレビュー13 | 手に持った松明が柱に落とす影の縁を滑らかにし、奥に隠れた葉や幹の照明計算を減らした。 | `python3 tools/build.py --visible-terrain-preview` | [Aqualumen-1.9.0-preview.13.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.13.zip) | [検証記録](reports/2026-11-23-wet-receiver/README.md) |
| 1.9.0 プレビュー12 | 幹が松明の火全体を隠す場所で影の計算を短縮した。 | `python3 tools/build.py --torch-umbra-preview` | [Aqualumen-1.9.0-preview.12.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.12.zip) | [検証記録](reports/2026-11-23-torch-umbra/README.md) |
| Hand-Penumbra-Study | 手持ち松明の半影。松明で幹を左右から照らしても壁の影の縁に滑らかな濃淡が出る。 | `python3 tools/build.py --torch-umbra-preview && python3 reports/2026-11-23-torch-penumbra/joint_pack.py` | [Aqualumen-Hand-Penumbra-Study.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-Hand-Penumbra-Study.zip) | [検証記録](reports/2026-11-23-torch-penumbra/README.md) |
| 1.9.0 プレビュー11 | 松明の光が葉から地面に返り、幹で直射光が遮られた場所にも葉の色がわずかに映る。 | `python3 tools/build.py --leaf-return-preview` | [Aqualumen-1.9.0-preview.11.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.11.zip) | [検証記録](reports/2026-11-23-leaf-tiles/README.md) |
| 1.9.0 プレビュー10 | 松明の光が壁や天井で二回反射する計算を、近くの同じ向きの面ごとにまとめた。 | `python3 tools/build.py --face-preview` | [Aqualumen-1.9.0-preview.10.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.10.zip) | [検証記録](reports/2026-11-23-torch-density/README.md) |
| 1.9.0 プレビュー8 | 洞窟の中から昼の空を見上げると手前の岩肌が暗くなり入口の白飛びが抑えられる。岩壁に向き直ると目がゆっくり順応する。 | `python3 tools/build.py --eye-preview` | [Aqualumen-1.9.0-preview.8.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.8.zip) | [検証記録](reports/2026-11-22-eye-adaptation/README.md) |
| 1.9.0 プレビュー7 | ランタンの光が二枚の壁で反射して灯りの見えない天井に届く。木陰では手持ち松明が日射の影を暖色で照らす。 | `python3 tools/build.py --ceiling-preview` | [Aqualumen-1.9.0-preview.7.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.7.zip) | [検証記録](reports/2026-11-22-ceiling-return/README.md) |
| 1.9.0 プレビュー6 | 日なたの床の色が牛を照らし、夜は二つの灯りの間を歩く牛の影が壁に色を残す。 | `python3 tools/build.py --animal-preview` | [Aqualumen-1.9.0-preview.6.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.6.zip) | [検証記録](reports/2026-11-21-animal-light/README.md) |
| 1.9.0 プレビュー5 | 木陰の白樺を松明と魂の松明で両側から照らせる。地面の材質と木漏れ日から地面への反射光を計算する。 | `python3 tools/build.py --ground-preview` | [Aqualumen-1.9.0-preview.5.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.5.zip) | [検証記録](reports/2026-11-21-ground-return/README.md) |
| 1.9.0 プレビュー4 | 木陰に届く空の光を、周囲の葉や土がどの方向を塞いでいるかから求める。 | `python3 tools/build.py --canopy-preview` | [Aqualumen-1.9.0-preview.4.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.4.zip) | [検証記録](reports/2026-11-21-canopy-sky/README.md) |
| 1.9.0 プレビュー3 | 溶岩を面光源として扱う。柱の奥の魂の松明が壁を青く照らし、半透明の向こうの壁にも届いた光を計算する。 | `python3 tools/build.py --lava-preview` | [Aqualumen-1.9.0-preview.3.zip](https://github.com/kusutohu1128/aqualumen/releases/download/experiments-2026-11-23/Aqualumen-1.9.0-preview.3.zip) | [検証記録](reports/2026-11-21-lava-light/README.md) |

## ビルドと検査

```sh
python3 tools/build.py --release                # dist/Aqualumen-1.8.0.zip
python3 tools/build.py --help                   # 実験版・プレビューのビルドフラグ一覧
bash tools/build-lighting-compiler.sh            # dist/aqualumen-lighting-compiler-0.3.0.jar
bash tools/build-physics-mod.sh                  # dist/aqualumen-physics-0.3.0.jar（開発中の候補。配布版は0.2.0）
make check                                       # release/shaders の検査
make check-development                           # shaders/ の検査
```

`make check` は `release/shaders`（`--play-release`）の描画プログラムを実機GPUでコンパイル・リンクし、雨よけプローブを実行します。EGLとlibepoxyの開発ファイルが必要です。機能ごとの検査は `make check-lava`、`make check-canopy`、`make check-ground`、`make check-animal`、`make check-ceiling`、`make check-eye`、`make check-face` などです。照明コンパイラのビルドは、Prism Launcherに導入したMinecraft 1.21.1用のJava 21と依存ライブラリを使い、Prismのデータディレクトリは環境変数 `AQUALUMEN_PRISM_ROOT` で指定できます。生成したファイルは `dist/` に出力されます。

## リポジトリ構成

| パス | 内容 |
|---|---|
| [release/shaders/](release/shaders) | 1.8.0通常版のシェーダーソース |
| `release/<variant>/` | 実験版・プレビューの重ねるレイヤー（`tools/build.py` のフラグで積層） |
| [shaders/](shaders) | 開発中の別系統ツリー |
| [physics-mod/](physics-mod) | 接触波紋用クライアントMod |
| [compiler-mod/](compiler-mod) | 照明コンパイラ 0.3.0（面光源プレビュー用） |
| [tools/](tools) | ビルド・検査スクリプト |
| [reports/](reports) | 検証記録 |
| [docs/](docs) | 機能・実験・開発記録 |

## 開発記録

- [docs/FEATURES.md](docs/FEATURES.md) — 1.8.0の機能詳細
- [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md) — 実験版と1.9.0プレビューの記録
- [docs/HISTORY.md](docs/HISTORY.md) — 0.6と実験版の開発記録
- [reports/](reports/) — 各検証の記録と実画像

## 貢献

バグ報告・シェーダーの修正・ドキュメントの改善を受け付けています。開発環境と検査の手順は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## 参考文献

**水と光学**

- [濡れた材質の光学モデル](https://doi.org/10.2312/egwr/egwr99/273-282)（[同論文の別表記DOI](https://doi.org/10.2312/EGWR/EGWR99/273-282)）
- [PBRTの微小面モデル](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory)
- [PBRTの散乱位相関数](https://pbr-book.org/4ed/Volume_Scattering/Phase_Functions)
- [微小な面における反射・屈折の参考文献（PBRT）](https://pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF)
- [PBRTの誘電体境界](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF)
- [Fresnel反射・Snell屈折](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission)
- [PBRT: 媒質の透過率](https://pbr-book.org/4ed/Volume_Scattering/Transmittance)（[www.pbr-book.org](https://www.pbr-book.org/4ed/Volume_Scattering/Transmittance)）: 色付き板ガラスの透過率をガラスの厚みから求める参考。係数はゲーム向けの近似値。
- [PBRT: 有限な媒質区間の光輸送](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/The_Equation_of_Transfer)
- [PBRT: 3次元格子のDDA走査](https://pbr-book.org/4ed/Volume_Scattering/Media): 各軸の次の格子境界までの距離を更新するアルゴリズムの参考。
- [Photonの降雨処理](https://github.com/sixthsurge/photon/blob/main/shaders/include/surface/rain_puddles.glsl)
- [NVIDIA: 波の物理モデル](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)
- [NVIDIA: GPU上の波動方程式](https://developer.nvidia.com/gpugems/gpugems2/part-vi-simulation-and-numerical-algorithms/chapter-44-gpu-framework-solving)
- [NVIDIA: 水底の集光](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)

**大気と雲**

- [Bruneton: 大気散乱](https://ebruneton.github.io/precomputed_atmospheric_scattering/)
- [環境光の方向と遮蔽](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)
- [Photonの拡散照明](https://github.com/sixthsurge/photon/blob/a715d94b45121e0825e40ba0029276b4378ce65d/shaders/include/lighting/diffuse_lighting.glsl)
- [地平角による環境遮蔽](https://developer.download.nvidia.com/presentations/2008/SIGGRAPH/HBAO_SIG08b.pdf)

**光源・影・光輸送**

- [Habel らの葉の透過光モデル](https://www.cg.tuwien.ac.at/research/publications/2007/Habel_2007_RTT/)
- [Jacquemoud と Baret の PROSPECT](https://www.sciencedirect.com/science/article/pii/003442579090100Z)
- [面光源の積分の参考文献（PBRT）](https://pbr-book.org/4ed/Light_Sources/Area_Lights)
- [光輸送方程式](https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/The_Light_Transport_Equation)
- [点光源と距離減衰（PBRT）](https://www.pbr-book.org/4ed/Light_Sources/Point_Lights)
- [Heitzらの多角形光源の積分](https://eheitzresearch.wordpress.com/415-2/)
- [Sutherland & Hodgman, Reentrant Polygon Clipping (1974)](https://doi.org/10.1145/360767.360802): 二つの遮蔽物が発光面に落とす影の共通部分を、影を表す半平面で凸多角形を順に切り詰めて計算する参考。
- [眼内散乱によるグレアの参考文献](https://www.graphics.cornell.edu/pubs/1995/SSZG95.pdf)
- [Microsoft: PCFとテクセルごとの受光面深度補正](https://learn.microsoft.com/en-us/windows/desktop/DxTechArts/cascaded-shadow-maps#calculating-a-per-texel-depth-bias-with-ddx-and-ddy-for-large-pcfs): 陸上影プレビューの考え方の参考。画面微分のコードは使わず、既存の非線形影座標を逆変換して各テクセル中心で受光平面の深度を求める独自実装。

**Iris・OpenGL**

- [Irisのブロック発光属性](https://shaders.properties/current/reference/attributes/at_midblock/)
- [Irisのカスタム画像](https://shaders.properties/current/reference/buffers/custom_images/)
- [Irisのシャドウ描画](https://shaders.properties/current/reference/programs/shadow/)
- [Irisのカラー添付](https://shaders.properties/current/reference/buffers/shadowcolor/)
- [Irisパイプライン](https://shaders.properties/current/reference/programs/overview/)
- [Iris: カメラと描画の座標系](https://shaders.properties/current/how-to/coordinate_spaces/)
- [Khronos OpenGL 4.6仕様](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf): 三角形の属性補間と遠近補正（§14.6・式14.9）、テクスチャ取得とミップ間補間（§§8.14.2–8.14.3）の基準。
- [Khronos: 深度比較サンプラー](https://wikis.khronos.org/opengl/Sampler_Object#Comparison_mode): 既存の比較モードを維持し、4点の比較結果を補間するための仕様上の参考。

**数値計算**

- [NIST DLMF: 不完全ガンマ関数の級数](https://dlmf.nist.gov/8.7.E1)・[連分数](https://dlmf.nist.gov/8.9.E2)・[erfcとの関係](https://dlmf.nist.gov/7.11.E2): TEST用のGaussian条件付きサンプラーのCDF評価の参考。
- [Mike Giles: 逆誤差関数の近似](https://people.maths.ox.ac.uk/~gilesm/codes/erfinv/): TEST用の逆Gaussian CDFの参考。係数はPythonの分位点から独立に生成し、既存の実装はコピーしていない。

**比較したシェーダーパック (Photon, Complementary)**

- [Photon v1.1](https://modrinth.com/shader/photon-shader/version/6FdrBtKp)
- [Complementary Unbound](https://modrinth.com/shader/complementary-unbound/version/Z1zqMzjh)
- [比較したPhotonの照明設定](https://github.com/sixthsurge/photon/blob/main/shaders/shaders.properties)

既存シェーダーパックのコード・有料アセットは使用していません。自作部分はMITライセンスです。
