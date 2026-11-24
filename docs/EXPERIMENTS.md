# 実験版と 1.9.0 プレビュー

通常版とは別にビルドして試す実験版と 1.9.0 プレビューの紹介です。

近くの色付き板ガラス越しに景色を見る実験版もあります。重ねた板の色と厚みによって、向こうのランタンや水底から届く光が変わります。Irisで試すときは照明コンパイラ0.3.0を使います。[シェーダーZIP](../dist/Aqualumen-Glass-View-Pass.zip)・[照明コンパイラ](../dist/aqualumen-lighting-compiler-0.3.0.jar)・[変更前との比較画像](../reports/2026-11-23-camera-glass/windows.png)・[測定記録](../reports/2026-11-23-camera-glass/README.md)

色付きの板ガラスを通った松明や日光が、奥の壁や床に色を落とす実験版を追加しました。晴れた午後、赤い窓を青い窓に替えると、ガラスを直接見ていない床にも違いが現れます。ビルドは `python3 tools/build.py --sunlit-panes` です。[実験版ZIP](../dist/Aqualumen-Sunlit-Panes.zip)・[日光を受ける床の比較](../reports/2026-11-23-stained-panes/sunlight.jpg)・[松明と色ガラスの実機検証](../reports/2026-11-23-stained-panes/README.md)

**松明と色ガラスを試す版**では、光が届く画面領域を調べ、必要な場所を窓用のシェーダーで描きます。窓に背を向けても、赤い光が当たる床や壁は着色されます。RTX 3080 Ti・1440pでは、赤窓の部屋が平均44.64 ms、窓を背にした白樺林・松明4本が84.98 msでした。ビルドは `python3 tools/build.py --window-tiles` です。[シェーダーZIP](../dist/Aqualumen-Window-Tiles.zip)・[全画素比較と実機計測](../reports/2026-11-23-screen-windows/README.md)

松明が板ガラスを照らすときだけ窓用の描画に切り替える版を追加しました。RTX 3080 Ti・1440pの赤窓の部屋では平均フレーム間隔が62.90 msから47.62 msに短縮し、白樺に松明4本を置いた場面では83.82 msから83.74 msでした。ビルドは `python3 tools/build.py --window-routing` です。[窓用のシェーダーZIP](../dist/Aqualumen-Window-Routing.zip)・[実機の画像と計測](../reports/2026-11-23-window-routing/README.md)

松明を持つと岩の模様が薄く見える場面向けに、明るさの中間域を調整する実験版を用意しました。岩壁、松明の炎、暗い面を同じ視点で比較できます。ビルドは `python3 tools/build.py --diffuse-display` です。[実験版ZIP](../dist/Aqualumen-Diffuse-Display.zip)・[ゲーム内の新旧比較](../reports/2026-11-23-stone-display/torch-stone.jpg)・[夕空と移動中の検証](../reports/2026-11-23-stone-display/README.md)

**松明の半影を保って軽くした実験版**では、地面から松明の炎までの間で、光を遮りうる範囲だけを探します。白樺林に松明を4本置いた場面で、RTX 3080 Ti・1440pの地形照明が平均57.46 msから36.23 msに短縮しました。白樺林の5視点で、同じ位置に届く松明の光を151万6,904件照合し、記録できる8ビットの可視率は全件一致しました。[シェーダーZIP](../dist/Aqualumen-Torch-Shadow-Rows.zip)・[比較と実機写真](../reports/2026-11-23-torch-brick-scan/README.md)

**複数のブロックが作る松明の半影を試せる画質優先版**では、幹や段差のどの部分が火を隠すかを調べます。白樺林の同じ草地でカメラを2 cm動かしたとき、火の可視率が66.7%から0%に飛んでいた場所が、39.6%から36.1%へなめらかに変化しました。独立計算では39.4%から36.0%です。RTX 3080 Ti・2560×1440・12チャンク・松明4本では平均105.97 ms（約9.4 fps）でした。ビルドは `python3 tools/build.py --torch-shadow-geometry` です。[画質優先版ZIP](../dist/Aqualumen-Torch-Shadow-Geometry.zip)・[夜の白樺林の画面](../reports/2026-11-23-torch-shadow-integral/settled-night-grass-geometry.png)・[地形2種類での実測](../reports/2026-11-23-torch-shadow-integral/joint-light.png)・[検証記録](../reports/2026-11-23-torch-shadow-integral/README.md)

**松明の影の輪郭を補正した実験版**では、火がブロックの角をかすめるときの遮光面積を安定させ、幹と段差が落とす二つの影を軽く計算します。RTX 3080 Ti・1440p・松明4本の白樺林で、従来の二つの影の版から平均フレーム間隔が78.92 msから69.01 msに短縮しました。カメラを2 cmずつ動かした同じ森の半影32,540件は、1件で1/255だけ変化しました。[実験版ZIP](../dist/Aqualumen-Torch-Shadow-Contours.zip)・[独立した光線との比較と実機計測](../reports/2026-11-23-torch-shadow-integral/README.md)

**幹と段差が作る松明の影を試せる実験版**です。幹の横に土を置くと、幹と土の間から見える火の大きさに応じて壁の影が変わります。同じ白壁で影の両側の明暗差を保ち、隣同士の画素の最大の輝度差が45行の平均で15.36階調から3.26階調になりました。RTX 3080 Ti・1440p・白樺林4灯で、配布用ZIPは平均78.41 ms（約12.8 fps）でした。ビルドは `python3 tools/build.py --placed-shadow-union-study` です。[実験版ZIP](../dist/Aqualumen-Placed-Torch-Shadows.zip)・[同じ壁の新旧比較](../reports/2026-11-23-mixed-occluders/paired-shadows.jpg)・[サバイバルの白樺](../reports/2026-11-23-mixed-occluders/survival.jpg)・[検証記録](../reports/2026-11-23-mixed-occluders/README.md)

**設置松明の半影実験版**では、木陰の地面に松明の光が届き、幹の奥には柔らかな縁の影が残ります。牛が松明の前を横切ると、その体が遮った分だけ影が重なります。白壁の影の縁で、隣り合う画素の最大の明るさの差は214本の走査線の平均で14.94階調から3.31階調に減りました。RTX 3080 Ti・1440p・松明4本の白樺林で、配布候補の平均フレーム間隔は68.43 msでした。ビルドは `python3 tools/build.py --placed-penumbra-animal-study` です。[実験版ZIP](../dist/Aqualumen-Placed-Penumbra-Animal-Study.zip)・[幹の影の拡大](../reports/2026-11-23-placed-penumbra/animal-ordinary-wall.png)・[牛が横切る場面](../reports/2026-11-23-placed-penumbra/animal-movement.jpg)・[検証記録](../reports/2026-11-23-placed-penumbra/README.md)

**設置松明のキャッシュ実験版**は、松明の光が遮られずに届く地形をワールド座標ごとに覚えます。水膜補正版と同じ白樺林・松明4本をRTX 3080 Tiの1440pで測り、平均フレーム間隔が2回とも約2.1 ms縮まりました。幹の設置・撤去と牛の横断も実ゲームで確認しています。[実験版ZIP](../dist/Aqualumen-Torch-Cell-Study.zip)・[木陰での6場面](../reports/2026-11-23-torch-open-volume/grove-light.jpg)・[条件と実測](../reports/2026-11-23-torch-open-volume/README.md)

**雨の石床の反射を直した試作版**では、水平な丸石を照らしたランタンの反射に現れる傾きを補正します。IrisとSodiumから渡る面の向きが約0.45度ずれるため、水膜があり、実際の三角形も水平な場所で上向きに戻しました。プレビュー13を土台にした独立したZIPです。[水膜の補正版](../dist/Aqualumen-Wet-Plane-Study.zip)・[暖色と青のランタンの実画面](../reports/2026-11-23-wet-receiver/corrected-stone-release/wet-leaf-cow-ingame.png)・[雨の降り始めと雨上がり](../reports/2026-11-23-wet-receiver/weather-cycle.jpg)・[岩陰で松明を持ち替えた比較](../reports/2026-11-23-wet-receiver/camp-hand-light.jpg)

**1.9.0 プレビュー13**では、手に持った松明が柱に落とす影の縁を滑らかにし、奥に隠れた葉や幹の照明計算を減らしました。RTX 3080 Ti・1440p・松明4本の白樺林で、同じ半影を描く前方描画版と比べ、平均フレーム間隔が79.73 msから66.76 msに縮まりました。配布用ZIPでの再計測は平均66.33 ms（約15 fps）でした。軽い室内では約1.3 ms増えます。雨の丸石を暖色と青のランタンで照らした検証では、不透明な床の照明を同じ露出で表示に換算した差は最大1階調でした。ビルドは `python3 tools/build.py --visible-terrain-preview` です。[プレビュー13のZIP](../dist/Aqualumen-1.9.0-preview.13.zip)・[雨の床の実画面](../reports/2026-11-23-wet-receiver/wet-floor.jpg)・[実機検証](../reports/2026-11-23-wet-receiver/README.md)

**1.9.0 プレビュー12**では、幹が松明の火全体を隠す場所で影の計算を短縮しました。白樺林に松明4本を置いた実ゲームで、平均フレーム間隔が74.46 msから72.40 msに短縮しました。松明を手に持って幹の左右に立つと壁の影が移動し、牛が暖色と青色の灯りを横切ると、一方の灯りだけが遮られます。[プレビュー12のZIP](../dist/Aqualumen-1.9.0-preview.12.zip)・[幹と牛の画面](../reports/2026-11-23-torch-umbra/moving-comparison.jpg)・[RTXでの計測](../reports/2026-11-23-torch-umbra/README.md)

**手持ち松明の半影を試す実験版**では、松明で幹を左から照らしても右から照らしても、壁に落ちる影の縁に滑らかな濃淡が出ます。柱の影が一段で約11階調変わっていた場所は約1階調になりました。同じRTX 3080 Tiで設置松明4本の白樺林を測ると、平均フレーム間隔がプレビュー12の72.40 msから79.58 msに増えたため、実験版を別のZIPにしました。実機検証の構成はMinecraft 1.21.1、Iris 1.8.8、Aqualumen Lighting Compiler 0.3.0です。[実験版ZIP](../dist/Aqualumen-Hand-Penumbra-Study.zip)・[壁の実画面](../reports/2026-11-23-torch-penumbra/joint-wall-comparison.png)・[性能と画質の検証](../reports/2026-11-23-torch-penumbra/README.md)

**1.9.0 プレビュー11**では、松明に照らされた葉から地面に光が返ります。幹で直射光が遮られた場所にも葉の色がわずかに映ります。固定したオーク林の画面では、幹の裏の草703地点で、暖色の松明による表示輝度が中央値3.07階調上がりました。RTX 3080 Ti・1440p・白樺林に松明4本で、GPUフレーム時間はプレビュー10の61.15 msから65.47 msになりました。ビルドは `python3 tools/build.py --leaf-return-preview` です。[プレビュー11](../dist/Aqualumen-1.9.0-preview.11.zip) · [実画面の比較](../reports/2026-11-23-leaf-tiles/forest-display.png) · [測定条件と限界](../reports/2026-11-23-leaf-tiles/README.md)

**1.9.0 プレビュー10**では、松明の光が壁や天井で二回反射する計算を、近くにある同じ向きの面ごとにまとめました。白樺の木陰に松明を4本置いた場面で、RTX 3080 Ti・1440pのGPU時間がプレビュー8から約4〜5 ms短くなりました。固定入力6条件で反射光の出力は元の版と全画素一致しました。ビルドは `python3 tools/build.py --face-preview` です。[プレビュー10](../dist/Aqualumen-1.9.0-preview.10.zip) · [白樺と砂州の実画面](../reports/2026-11-23-torch-density/brightness-and-count.jpg) · [GPUと実フレームの測定](../reports/2026-11-23-torch-density/README.md)

**1.9.0 プレビュー8**では、洞窟の中から昼の空を見上げると、手前の岩肌が暗くなり、入口の白飛びが少し抑えられます。岩壁に向き直ると目がゆっくり暗さに慣れ、岩肌がまた見えてきます。昼の雪村の家ではプレビュー7と見分けがつきませんでした。NVIDIAではプレビュー3〜7と同じコンパイル用Mod 0.3.0が必要です。ビルドは `python3 tools/build.py --eye-preview` です。[プレビュー8](../dist/Aqualumen-1.9.0-preview.8.zip) · [洞窟の入口を見上げた比較](../reports/2026-11-22-eye-adaptation/cave-opening.jpg) · [露出とフレーム時間の実測](../reports/2026-11-22-eye-adaptation/README.md)

**1.9.0 プレビュー7**では、ランタンの光が二枚の壁で反射して、灯りの見えない天井に届きます。白い壁を赤く替えると、奥の天井に返る色が変わります。木陰では手持ちの松明が日射の影を暖色で照らし、魂の松明に持ち替えると同じ幹が青みを帯びます。雪の村では、普通のランタンが点いた家に魂の松明を一つ置いた状態から遊べます。ビルドは `python3 tools/build.py --ceiling-preview` です。[プレビュー7](../dist/Aqualumen-1.9.0-preview.7.zip) · [木陰での持ち替え](../reports/2026-11-21-animal-light/woodland/torchlight.jpg) · [雪村の写真](../reports/2026-11-22-ceiling-return/village/homecoming.jpg) · [家の中から遊べるセーブ](../dist/Aqualumen-Homecoming.zip) · [反射の実測](../reports/2026-11-22-ceiling-return/README.md)

**1.9.0 プレビュー6**では、日なたの赤い床が牛の脇腹を赤く照らし、屋根を掛けるとその色が引きます。夜は普通のランタンと魂のランタンの間を牛が歩くと、暖色が遮られた壁に青い影が、青が遮られた壁に暖色の影ができます。ビルドは `python3 tools/build.py --animal-preview` です。[プレビュー6](../dist/Aqualumen-1.9.0-preview.6.zip) · [二灯の間を歩く牛](../reports/2026-11-21-animal-light/crossing.mp4) · [毛に返る床の色](../reports/2026-11-21-animal-light/coat.jpg) · [光源別の実測とフレーム時間](../reports/2026-11-21-animal-light/README.md)

**1.9.0 プレビュー5**では、木陰の白樺を松明と魂の松明で両側から照らせます。片方との間に石を積むと、幹のその側で暖色が弱まり、青い灯りは残ります。日中は、近くの地面の材質と木漏れ日を使って、地面から幹や壁に返る光を計算します。プレビューのビルドは `python3 tools/build.py --ground-preview` です。[プレビュー5](../dist/Aqualumen-1.9.0-preview.5.zip) · [松明二本と石壁の実画面](../reports/2026-11-21-ground-return/lights/two-lamps.jpg) · [白床・赤床・屋根の比較](../reports/2026-11-21-ground-return/play/birch.jpg) · [松明を残して歩く実プレイ](../reports/2026-11-21-ground-return/walk/walk.mp4) · [計算方法とRTX 3080 Tiでの実測](../reports/2026-11-21-ground-return/README.md) · [参照した光輸送方程式](https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/The_Light_Transport_Equation)

1.9.0プレビュー3では、溶岩を面光源として扱います。石柱の手前の溶岩が壁に届かなくても、柱の奥に置いた魂の松明は壁を青く照らします。天然洞窟で溶岩を水で固めると、黒曜石の手前には松明の青、奥に残った溶岩の近くには橙色が残ります。半透明の物体を通して壁を見るときも、壁に届いた光を計算してから手前の色を重ねます。[1.9.0プレビュー3](../dist/Aqualumen-1.9.0-preview.3.zip) · [石柱と魂の松明の実画面](../reports/2026-11-21-lava-light/wall-v190/split-rtx-compare/torch-with-lava.jpg) · [半透明の実体を通して見た壁](../reports/2026-11-21-lava-light/wall-v190/glass-order-comparison/glass.jpg) · [Heitzらの多角形光源の積分](https://eheitzresearch.wordpress.com/415-2/)

1.9.0プレビュー4では、木陰に届く空の光を、周囲の葉や土がどの方向を塞いでいるかから求めます。同じ白樺を撮ると、奥まった草の段差は暗く、空に開いた草は明るく残ります。幹の手前に松明を立てると橙色、魂の松明に替えると青みが戻ります。RTX 3080 Ti・2560×1440・12チャンクで、この視点の平均は消灯32.4、松明23.8、魂の松明24.1 FPSでした。`python3 tools/build.py --canopy-preview` でZIPを作り、`make check-canopy` で方向別の遮蔽とカメラ移動時の連続性を検査できます。[プレビュー4](../dist/Aqualumen-1.9.0-preview.4.zip) · [サバイバルで松明の光を土で遮った比較](../reports/2026-11-21-canopy-sky/shaded-oak/oak.jpg) · [白樺の消灯・点灯比較](../reports/2026-11-21-canopy-sky/daylight/birch.jpg) · [木陰の拡大](../reports/2026-11-21-canopy-sky/daylight/shade.jpg) · [計算と実機検証](../reports/2026-11-21-canopy-sky/README.md) · [Photonの拡散照明](https://github.com/sixthsurge/photon/blob/a715d94b45121e0825e40ba0029276b4378ce65d/shaders/include/lighting/diffuse_lighting.glsl) · [環境光の方向と遮蔽](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)

天然洞窟の体験用セーブでは、岩棚の上から魂の松明とバケツを使えます。ZIP内の `Aqualumen-Lava-Cavern` を `saves/` に展開すると、シード308060のサバイバル地形が初回に生成されます。[体験用セーブ](../dist/Aqualumen-Lava-Cavern.zip) · [溶岩と魂の松明の実画面](../reports/2026-11-21-lava-light/cavern/ordered-survival/cavern-light.jpg)

NVIDIAでプレビューを使うときは、対応するコンパイル用Modを `mods/` に置いてMinecraftを再起動し、Irisからプレビューを選べます。対象は Minecraft 1.21.1、Iris 1.8.8、Sodium 0.6.9 です。このModはAqualumenの面光源シェーダーにだけドライバーのコンパイル設定を適用します。水面の接触波紋には従来のphysics 0.2を併用できます。[コンパイル用Mod 0.3.0](../dist/aqualumen-lighting-compiler-0.3.0.jar) ビルドは `python3 tools/build.py --lava-preview` と `bash tools/build-lighting-compiler.sh` で再現できます。 `make check-lava` はプレビューZIPを展開し、通常版との光源比較を含めてGPUで検査します。

RTX 3080 Ti・12チャンクで、プレビュー3の昼の白樺は2560×1440で平均33.0 FPS（消灯）、24.9 FPS（松明）、24.1 FPS（魂の松明）でした。天然洞窟を歩いて採掘と水バケツを試したときは1600×900でF3表示の中央値14 FPSでした。どちらもこのPCの隔離したMinecraftで計測しています。[同じ白樺の比較](../reports/2026-11-21-lava-light/wall-v190/birch-release-comparison/birch.jpg) · [フレーム時間](../reports/2026-11-21-lava-light/wall-v190/birch-preview3-final/timing.json) · [洞窟を再び開いた実画面](../reports/2026-11-21-lava-light/cavern/ordered-return/reopened.jpg)

このPCの **Aqualumen Lab** で選べる最新の任意パックはプレビュー10です。試すにはPrismのMod一覧で「Aqualumen Lighting Compiler」0.3.0を有効にして再起動し、Irisで「Aqualumen-1.9.0-preview.10.zip」を選んでください。通常の起動設定は1.8.0、physics 0.2.0、コンパイル用Modは無効です。[プレビュー10の配置と通常設定](../reports/2026-11-23-torch-density/lab.json)
