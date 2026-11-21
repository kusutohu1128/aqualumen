# Aqualumen 1.8.0

Minecraft Java 1.21.1 用の光と水のシェーダーです。木陰に松明を置くと、火の方を向いた幹や草に暖色の光が届きます。手に持って森や廃坑を歩くと、岩や葉を照らす位置が手と一緒に移り、反対の手に持ち替えると柱の影も移ります。魂の松明は青く、石壁は松明から届く光を遮ります。RTX 3080 Ti の通常プレイ向けに、浅瀬の砂が水に浸かると色が沈み、水面の裏に海底の段差が映ります。陸上では流れる雲が直射日光を遮り、樹木や石段には空の各方向から光が届きます。

**1.9.0 プレビュー8**では、洞窟の中から昼の空を見上げると、手前の岩肌が暗くなり、入口の白飛びが少し抑えられます。岩壁に向き直ると目がゆっくり暗さに慣れ、岩肌がまた見えてきます。昼の雪村の家ではプレビュー7と見分けがつきませんでした。NVIDIAではプレビュー3〜7と同じコンパイル用Mod 0.3.0が必要です。ビルドは `python3 tools/build.py --eye-preview` です。[プレビュー8](dist/Aqualumen-1.9.0-preview.8.zip) · [洞窟の入口を見上げた比較](reports/2026-11-22-eye-adaptation/cave-opening.jpg) · [露出とフレーム時間の実測](reports/2026-11-22-eye-adaptation/README.md)

**1.9.0 プレビュー7**では、ランタンの光が二枚の壁で反射して、灯りの見えない天井に届きます。白い壁を赤く替えると、奥の天井に返る色が変わります。木陰では手持ちの松明が日射の影を暖色で照らし、魂の松明に持ち替えると同じ幹が青みを帯びます。雪の村では、普通のランタンが点いた家に魂の松明を一つ置いた状態から遊べます。ビルドは `python3 tools/build.py --ceiling-preview` です。[プレビュー7](dist/Aqualumen-1.9.0-preview.7.zip) · [木陰での持ち替え](reports/2026-11-21-animal-light/woodland/torchlight.jpg) · [雪村の写真](reports/2026-11-22-ceiling-return/village/homecoming.jpg) · [家の中から遊べるセーブ](dist/Aqualumen-Homecoming.zip) · [反射の実測](reports/2026-11-22-ceiling-return/README.md)

**1.9.0 プレビュー6**では、日なたの赤い床が牛の脇腹を赤く照らし、屋根を掛けるとその色が引きます。夜は普通のランタンと魂のランタンの間を牛が歩くと、暖色が遮られた壁に青い影が、青が遮られた壁に暖色の影ができます。ビルドは `python3 tools/build.py --animal-preview` です。[プレビュー6](dist/Aqualumen-1.9.0-preview.6.zip) · [二灯の間を歩く牛](reports/2026-11-21-animal-light/crossing.mp4) · [毛に返る床の色](reports/2026-11-21-animal-light/coat.jpg) · [光源別の実測とフレーム時間](reports/2026-11-21-animal-light/README.md)

**1.9.0 プレビュー5**では、木陰の白樺を松明と魂の松明で両側から照らせます。片方との間に石を積むと、幹のその側で暖色が弱まり、青い灯りは残ります。日中は、近くの地面の材質と木漏れ日を使って、地面から幹や壁に返る光を計算します。プレビューのビルドは `python3 tools/build.py --ground-preview` です。[プレビュー5](dist/Aqualumen-1.9.0-preview.5.zip) · [松明二本と石壁の実画面](reports/2026-11-21-ground-return/lights/two-lamps.jpg) · [白床・赤床・屋根の比較](reports/2026-11-21-ground-return/play/birch.jpg) · [松明を残して歩く実プレイ](reports/2026-11-21-ground-return/walk/walk.mp4) · [計算方法とRTX 3080 Tiでの実測](reports/2026-11-21-ground-return/README.md) · [参照した光輸送方程式](https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/The_Light_Transport_Equation)

1.8.0 では、太陽や松明に背を向けた葉にも光が届きます。可視面の位置から葉の厚みと光源までの経路を求め、途中に幹、石壁、扉があればその光を遮ります。白い壁の前に葉と松明を置くと、壁に葉の隙間を通った光が映ります。ゲームのアトラスから葉の模様と色を読み、バイオームの色を合わせます。連なった樹冠の内側は平均的な減衰で近似しています。

同じ白樺の木陰で、松明を置くと幹の側面に暖色が入り、魂の松明に替えると青みが増します。葉越しの光は、炎の見かけの大きさに応じて影の縁がぼけます。RTX 3080 Ti、2560×1440、12チャンクのこの視点では、各10秒の平均は消灯49.6、松明31.3、魂の松明32.2 FPSでした。[木陰で点灯・消灯した実画面](reports/2026-11-21-leaf-light/timing-cone-daylight.jpg) · [白壁に落ちる葉の影の拡大](reports/2026-11-21-leaf-light/penumbra/cone-wall.jpg) · [オーク・シラカバ・サクラの違い](reports/2026-11-21-leaf-light/projected/cone-species.jpg)

葉の表と裏を別々に扱う考え方、色ごとの吸収・散乱、実際のゲーム画面の見え方を参考にしました。Aqualumen の透過率は Minecraft のテクスチャとブロック寸法に合わせた近似値です。[Habel らの葉の透過光モデル](https://www.cg.tuwien.ac.at/research/publications/2007/Habel_2007_RTT/) · [Jacquemoud と Baret の PROSPECT](https://www.sciencedirect.com/science/article/pii/003442579090100Z) · [Photon v1.1](https://modrinth.com/shader/photon-shader/version/6FdrBtKp)

雨の夜にランタンの下を歩くと、濡れた石に橙色の照り返しが伸びます。乾いた軒下には石そのものの質感が残り、魂のランタンに替えると近くを落ちる雨にも青い光が届きます。木の下では太陽の光と松明の光を別々に計算します。松明を外して戻すと、樹冠が落とす日の影を保ちながら、炎の届く幹や草の色が変わります。[木陰の松明を点けた実画像](reports/2026-11-21-door-light/birch.jpg) · [軒先の旧版と新版](reports/2026-11-21-rain-eaves/fixture/eaves-comparison.jpg) · [雨粒と水膜の検証](reports/2026-11-21-rain-eaves/README.md)

水膜では材質ごとの吸水と粗さを考慮し、GGXの微小面モデルで石に映る光の幅を求めます。雨粒では入射方向と視線のなす角に応じて光を散乱させます。Photonの降雨時の材質・天空光の条件を参照し、屋根の高さと光源までの遮蔽はAqualumen側で計算します。[濡れた表面の研究](https://doi.org/10.2312/EGWR/EGWR99/273-282) · [PBRTの微小面モデル](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory) · [PBRTの散乱位相関数](https://pbr-book.org/4ed/Volume_Scattering/Phase_Functions) · [Photonの降雨処理](https://github.com/sixthsurge/photon/blob/main/shaders/include/surface/rain_puddles.glsl)

夕暮れの家でダークオークの扉を閉めると、隣室のランタンから床へ差し込んでいた暖色が引きます。オークの扉は上部の四つの小窓から、アカシアの扉は細い格子の間から光を通します。ゲームが使う扉のテクスチャと厚さを読み、ランタンの発光面から各隙間を見通せる割合で、壁に落ちる光の縁をぼかします。[ゲーム内の扉による投影](reports/2026-11-21-door-light/window/shipped-projection.jpg) · [半影の拡大比較](reports/2026-11-21-door-light/window/shipped-edge-comparison.jpg) · [面光源の積分の参考文献（PBRT）](https://pbr-book.org/4ed/Light_Sources/Area_Lights)

松明と魂の松明を両手に持つと、岩に暖色と青い光が同時に届きます。手ぶらに戻せば元の暗さに戻ります。露出は目の前の面に実際に届いた光に応じて変化し、地上が正午でも、閉じた廃坑では暗所に順応します。[森の昼と夜](reports/2026-11-21-carried-light/polished-forest.jpg) · [廃坑の両手比較](reports/2026-11-21-carried-light/polished-mine.jpg) · [検証記録](reports/2026-11-21-carried-light/README.md)

柱の陰でランタンが直接見えない白壁にも、近くの赤いコンクリートで反射した光が届きます。赤壁を磨かれた深層岩に替えると白壁の赤みが弱まり、二面の間に石の仕切りを立てると反射光が遮られます。反射の計算にはゲームが描くブロックのテクスチャを使います。対象は近くの不透明な立方体の面で、光源からの拡散反射を一回まで追います。「光」の設定から「松明・ランタンの間接光」を切り替えられます。[1.6.0で木陰の松明を点けた実画像](reports/2026-11-21-door-light/birch.jpg) · [反射光の検証記録](reports/2026-11-21-indirect-light/README.md) · [光輸送方程式](https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/The_Light_Transport_Equation)

1.4プレビューで導入した、生き物が局所光に落とす影も通常版に含みます。牛の頭・胴・脚が光を遮り、小麦を追って歩くと影も壁の上を移動します。[1.4.0 プレビュー](dist/Aqualumen-1.4.0-preview.1.zip) · [実ゲーム動画](reports/2026-11-21-mob-light/living-walk/wheat-follow.mp4) · [通常版との比較](reports/2026-11-21-mob-light/README.md)

1.9.0プレビュー3では、溶岩を面光源として扱います。石柱の手前の溶岩が壁に届かなくても、柱の奥に置いた魂の松明は壁を青く照らします。天然洞窟で溶岩を水で固めると、黒曜石の手前には松明の青、奥に残った溶岩の近くには橙色が残ります。半透明の物体を通して壁を見るときも、壁に届いた光を計算してから手前の色を重ねます。[1.9.0プレビュー3](dist/Aqualumen-1.9.0-preview.3.zip) · [石柱と魂の松明の実画面](reports/2026-11-21-lava-light/wall-v190/split-rtx-compare/torch-with-lava.jpg) · [半透明の実体を通して見た壁](reports/2026-11-21-lava-light/wall-v190/glass-order-comparison/glass.jpg) · [Heitzらの多角形光源の積分](https://eheitzresearch.wordpress.com/415-2/)

1.9.0プレビュー4では、木陰に届く空の光を、周囲の葉や土がどの方向を塞いでいるかから求めます。同じ白樺を撮ると、奥まった草の段差は暗く、空に開いた草は明るく残ります。幹の手前に松明を立てると橙色、魂の松明に替えると青みが戻ります。RTX 3080 Ti・2560×1440・12チャンクで、この視点の平均は消灯32.4、松明23.8、魂の松明24.1 FPSでした。`python3 tools/build.py --canopy-preview` でZIPを作り、`make check-canopy` で方向別の遮蔽とカメラ移動時の連続性を検査できます。[プレビュー4](dist/Aqualumen-1.9.0-preview.4.zip) · [サバイバルで松明の光を土で遮った比較](reports/2026-11-21-canopy-sky/shaded-oak/oak.jpg) · [白樺の消灯・点灯比較](reports/2026-11-21-canopy-sky/daylight/birch.jpg) · [木陰の拡大](reports/2026-11-21-canopy-sky/daylight/shade.jpg) · [計算と実機検証](reports/2026-11-21-canopy-sky/README.md) · [Photonの拡散照明](https://github.com/sixthsurge/photon/blob/a715d94b45121e0825e40ba0029276b4378ce65d/shaders/include/lighting/diffuse_lighting.glsl) · [環境光の方向と遮蔽](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-17-ambient-occlusion)

天然洞窟の体験用セーブでは、岩棚の上から魂の松明とバケツを使えます。ZIP内の `Aqualumen-Lava-Cavern` を `saves/` に展開すると、シード308060のサバイバル地形が初回に生成されます。[体験用セーブ](dist/Aqualumen-Lava-Cavern.zip) · [溶岩と魂の松明の実画面](reports/2026-11-21-lava-light/cavern/ordered-survival/cavern-light.jpg)

NVIDIAでプレビューを使うときは、対応するコンパイル用Modを `mods/` に置いてMinecraftを再起動し、Irisからプレビューを選べます。対象は Minecraft 1.21.1、Iris 1.8.8、Sodium 0.6.9 です。このModはAqualumenの面光源シェーダーにだけドライバーのコンパイル設定を適用します。水面の接触波紋には従来のphysics 0.2を併用できます。[コンパイル用Mod 0.3.0](dist/aqualumen-lighting-compiler-0.3.0.jar) ビルドは `python3 tools/build.py --lava-preview` と `bash tools/build-lighting-compiler.sh` で再現できます。 `make check-lava` はプレビューZIPを展開し、通常版との光源比較を含めてGPUで検査します。

RTX 3080 Ti・12チャンクで、プレビュー3の昼の白樺は2560×1440で平均33.0 FPS（消灯）、24.9 FPS（松明）、24.1 FPS（魂の松明）でした。天然洞窟を歩いて採掘と水バケツを試したときは1600×900でF3表示の中央値14 FPSでした。どちらもこのPCの隔離したMinecraftで計測しています。[同じ白樺の比較](reports/2026-11-21-lava-light/wall-v190/birch-release-comparison/birch.jpg) · [フレーム時間](reports/2026-11-21-lava-light/wall-v190/birch-preview3-final/timing.json) · [洞窟を再び開いた実画面](reports/2026-11-21-lava-light/cavern/ordered-return/reopened.jpg)

このPCの **Aqualumen Lab** で選べる最新の任意パックはプレビュー8です。試すにはPrismのMod一覧で「Aqualumen Lighting Compiler」を有効にして再起動し、Irisで「Aqualumen-1.9.0-preview.8.zip」を選んでください。普段の起動設定は1.8.0で、コンパイル用Modは無効です。[プレビュー8の配置と設定](reports/2026-11-22-eye-adaptation/lab.json)

暗いオークの幹の前で灯りを取り出し、洞窟へ下りて水辺へ戻るところを、同じ道で二度撮影しました。[夕暮れの松明・41秒](reports/2026-11-21-continuous-walk/dusk-walk-final/walk.mp4) · [雨の夜のランタン・29秒](reports/2026-11-21-continuous-walk/rain-bank/walk.mp4)

## このPCで遊ぶ

Prism Launcher で **Aqualumen Lab** を起動してください。Esc → 設定 → ビデオ設定 → シェーダーパックで `Aqualumen-1.8.0.zip` を選べます。水に入って見上げると、空が丸く収まり、その縁が波に合わせて動きます。水面で全反射する角度では水中の景色が映ります。通常プレイには計測用Modもワールドの切り替えも不要です。

「シングルプレイ」から **Aqualumen Rain Walk** を開くと、雨の降る夕方、ランタンを吊った軒先に立ちます。北の道を進むと右手に松明の付いた木があり、その先の坑道を抜けると池に出ます。1番は空の手、2番は松明、3番と4番は通常と魂のランタンです。昼夜と天気は自然に進みます。別の環境ではZIP内の `Aqualumen-Rain-Walk` を `saves/` に展開してください。[遊べる雨の散歩道](dist/Aqualumen-Rain-Walk.zip) · [雨と晴れの木陰で松明を付け外しした比較](reports/2026-11-21-rain-eaves/journey/run-7/oak-torch.jpg) · [松明と魂のランタンを片方ずつ消す](reports/2026-11-21-rain-eaves/journey/run-8/two-lights.jpg) · [坑道と池を巡る約30秒の映像](reports/2026-11-21-rain-eaves/journey/run-7/walk-highlights.mp4)

「シングルプレイ」から **Aqualumen Woodland** を開くと、自然生成のオークの西側に立ちます。2番が松明、3番が魂の松明、1番が空の手です。木の北と南に一本ずつ置いて1番に戻し、片方だけ回収すると、残った光が届く面を見比べられます。木の西に水辺、東の斜面に石の洞穴があります。初回にMinecraftが地形を生成します。[遊べる森](dist/Aqualumen-Woodland.zip) · [サバイバルで松明を置いた場面](reports/2026-11-21-leaf-light/play/release-roundtrip/woodland-lights.jpg) · [夜の岸から見た水面](reports/2026-11-21-leaf-light/play/slope-return/water-surface.png)

**Aqualumen Snow Village** では、夕方、雪の降る村の小道から始まります。正面のトウヒの家には軒先に二つのランタンがあります。空の手で扉を開け、東側の階段から中に入り、3番の魂の松明を持つと窓や床に青い光が届きます。最初の降水を設定してあり、その後は通常の昼夜と天気が進みます。[遊べる雪村](dist/Aqualumen-Snow-Village.zip) · [通常プレイで家の扉を開けて中に入る](reports/2026-11-21-settlement-light/playable/village-house.jpg)

「シングルプレイ」から **Aqualumen Lantern House** を開くと、夕暮れの並木道に立ちます。9番の空きスロットで木の幹の松明を外し、1番で置き直すと、幹に届く明かりを見比べられます。道の先の家では、手を空けて二部屋の間の扉を右クリックすると白い床の暖色が変わります。別のPCではワールドZIPを展開し、中の `Aqualumen-Lantern-House` フォルダを `saves/` に入れてください。[遊べるワールド](dist/Aqualumen-Lantern-House.zip) · [玄関までの道](reports/2026-11-21-door-light/playable/smoke/01-spawn.png) · [同じ家で二灯と扉を操作した実画像](reports/2026-11-21-door-light/sky-control/ordinary-house.jpg) · [扉を開閉した動画](reports/2026-11-21-door-light/interaction/shipped/lever-door.mp4)

- [シェーダー 1.8.0](dist/Aqualumen-1.8.0.zip) を `shaderpacks/` に、[接触波紋用Mod 0.2.0](dist/aqualumen-physics-0.2.0.jar) を `mods/` に入れます。対応環境は Java 21、Fabric、Iris 1.8.8、Sodium 0.6.9 です。
- 標準設定は `BALANCED`。遠近の影と水面を2560×1440・描画12チャンクで検証しています。以前の水の見え方に戻したいときは、Labに残してある `Aqualumen-0.6.0.zip` を選べます。
- [1.0.1との実ゲーム比較](reports/2026-11-20-shore-light/comparison.jpg)、[同じ岸で見たPhoton・Complementaryとの違い](reports/2026-11-20-shore-light/reference-comparison.jpg)、[動画・条件別のフレーム時間](reports/2026-11-20-shore-light/README.md)を確認できます。

松明・ランタン・焚き火・シーランタンなどはブロックの位置と発光状態から取得します。太陽、月、複数の設置光源の照度を面ごとに加算します。松明には近距離で発散しない逆二乗減衰を使い、葉は通過距離に応じて減光します。色付きガラスの透過色と炎の色は演出用の近似です。光源の周囲14ブロックを計算し、8ブロック四方の各立方体で最大12灯を選びます。視点から19〜24ブロックで通常のブロック光へ移行します。松明を置いていない場所でも、溶岩や未登録の発光ブロックには従来の照明が効きます。[点光源と距離減衰（PBRT）](https://www.pbr-book.org/4ed/Light_Sources/Point_Lights) · [Irisのブロック発光属性](https://shaders.properties/current/reference/attributes/at_midblock/) · [比較したPhotonの照明設定](https://github.com/sixthsurge/photon/blob/main/shaders/shaders.properties)

夜に松明のある部屋に入ると、壁に届いた光に合わせて露出が落ち着きます。暗がりへ戻るとゆっくり回復します。炎のごく近くには淡い光のにじみが現れます。Irisのシェーダー設定から、夜の露出順応と光源のにじみを個別に調整できます。[実際の森での点灯比較](reports/2026-11-20-local-light/forest-final.jpg) · [石壁・色ガラス・複数光源](reports/2026-11-20-local-light/placed-lights-final.jpg) · [動画と実測結果](reports/2026-11-20-local-light/README.md) · [眼内散乱によるグレアの参考文献](https://www.graphics.cornell.edu/pubs/1995/SSZG95.pdf)

水深3.25 mから見上げた1.0.1では、波と雲が重なって生じる細い縞の明暗を、一画素が受ける光の量に合わせて和らげています。[1.0.0との実ゲーム比較](reports/2026-11-20-underwater-refinement/comparison.jpg) · [検証条件と動画](reports/2026-11-20-underwater-refinement/README.md) · [微小な面における反射・屈折の参考文献（PBRT）](https://pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF)

## 描画とビルド

水中で見上げたとき、カメラから隠れた岸は、影を描く際に得た周囲32×24×32ブロックの実際の面と交差判定します。砂と砂利が濡れたときの散乱低下には二流束モデルを採用しました。表面の波紋には、雨粒が水に当たって広がる短い重力・表面張力波も加えています。 浅瀬の泡は、波が浅い水底に乗り上げて崩れる条件で現れます。草岸や石段のそばでは、近くの地形が遮る空の光を画面の深度から推定します。[濡れた材質の光学モデル](https://doi.org/10.2312/egwr/egwr99/273-282) · [地平角による環境遮蔽](https://developer.download.nvidia.com/presentations/2008/SIGGRAPH/HBAO_SIG08b.pdf) · [Irisのカスタム画像](https://shaders.properties/current/reference/buffers/custom_images/) · [外観の比較に用いたPhoton](https://modrinth.com/shader/photon-shader/version/6FdrBtKp) · [Complementary Unbound](https://modrinth.com/shader/complementary-unbound/version/Z1zqMzjh)

水面では波の傾きから屈折・Fresnel反射・全反射を計算します。カメラから隠れた砂底を探すため、影を描くときに実際に見えた地形の位置・材質・照明を記録し、屈折した光線が横切る順にブロックと交差させます。浅い水では水底までの距離に応じて光が減衰し、水底で跳ね返った日光が水中の段差を照らします。影の視点からも隠れた地形・植物は近似になります。太陽は見かけの直径を約0.53度に保ち、大気の前方散乱によってその周囲を明るくしています。[Irisのシャドウ描画](https://shaders.properties/current/reference/programs/shadow/) · [Irisのカラー添付](https://shaders.properties/current/reference/buffers/shadowcolor/) · [PBRTの誘電体境界](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF)

通常版のGLSLは [release/shaders](release/shaders) にあります。リポジトリのルートで `python3 tools/build.py` を実行すると同じZIPを生成します。`make check` は通常版の描画プログラムをコンパイル・リンクし、波紋のcompute更新、屈折、吸収、大気と遮蔽をGPUで検査します。開発中の別系統は [shaders](shaders) にあり、ビルドは `python3 tools/build.py --development`、検査は `make check-development` です。

---

# 0.6と実験版の開発記録

以下のバージョン、選択中のパック、起動状態は各検証を行った当時の記録です。


Minecraft Java版向けのオリジナルIrisシェーダーと水面インタラクションModです。0.3では水と体積雲を改善し、0.3.1で遠方の雲の重なり、0.3.2で陸上の不自然な霞を修正しました。0.3.3では、水中から空を見上げる際の四角い継ぎ目・重複を修正しています。0.4では、水底の集光を受光面の直射太陽光だけに限定し、再現できた滑らかな水底での屈折切り替わりを修正しました。0.5では、確定した水底へ入る太陽光に水面の反射損失と入射光路の減衰を加えています。0.6では、制御された岸辺で失われていた水底の光を追跡し直し、太陽円盤の積分光量を地形の直射光と合わせました。自然な屈折・全反射による「スネルの窓」は残します。画質優先の実験版で、自然の浅瀬の強い青緑色・岸際の鋭い境界などは未解決です。実写級の完成品や完全な流体シミュレーターではありません。

## このPCで使う

Prism Launcherの **Aqualumen Lab** を起動してください。新版シェーダーと専用Modを有効にしてあります。通常ワールドへの検証用カメラ・時刻・地形の自動操作は行っていません。検証Modと有効化マーカーは通常利用時には無効です。0.6の引き渡し時点では通常アカウントのゲームを起動し、一時停止しています。

- Minecraft 1.21.1 / Java 21 / Fabric Loader 0.19.5
- Iris 1.8.8 / Sodium 0.6.9
- RTX 3080 Ti / 12 GB、OpenGL 4.3以上必須
- Ryzen 9 5900X / RAM 48 GB、専用インスタンスはJava 21 Generational ZGC・ヒープ2〜6 GB
- 測定条件は2560×1440、描画12・シミュレーション6チャンク、標準 `BALANCED`。FPS設定と実測値は各記録に保存します。
- 通常起動は画面に収まる1600×900ウィンドウ・上限120 FPS。F11で画面全体へ切り替えられます。
- ユーザーの方針変更に合わせ、画質を優先します。FPSは観測値として記録し、最低60 FPS保証や合否条件にはしません。

配布物: [シェーダーZIP](dist/Aqualumen-0.6.0.zip) / [専用Mod](dist/aqualumen-physics-0.2.0.jar)。描画側の更新なので専用Modは検証済みの0.2をそのまま使います。別の対応環境では、それぞれ `shaderpacks` と `mods` に入れてIrisから選択します。ZIPだけでも光学・風波は使えますが、接触波紋とディメンション判定にはModが必要です。ModはMinecraft 1.21.1 / Iris 1.8.8のAPIに固定しています。

設定は軽量・標準・高画質です。まず標準を使い、実際の負荷に応じて軽量へ変更してください。

## 水と光

風波は24成分（軽量12・高画質32）の方向性を持つ有限Fourierスペクトルです。重力・表面張力の分散関係、解析的な勾配・曲率、ピクセル幅による帯域制限を使います。未解像の傾斜分散を反射の粗さに移します。FFT海洋シミュレーターではありません。

Fresnel反射・Snell屈折・水中からの全反射・RGB別のBeer–Lambert減衰を実装しています。画面内の深度から屈折光路を反復推定し、浅瀬の初期光路は局所水深と屈折方向から求めます。画面外の反射は環境色へフォールバックします。水中の散乱色を空・太陽・月・ブロック光に結び付け、無照明の水自身は発光しません。RGB値は選んだ澄んだ水の外観であり、実測海水の分光校正ではありません。水底のコースティクスは波面の曲率と有限な光源幅から光束の広がりを推定する、明るさ制限付きの近似です。

0.3.3では、水中の屈折先を「収束した不透明地形」「画面上で空を観測」「未確定」に分けます。地形は従来の画面内追跡、空は屈折した世界方向から雲・大気・太陽・月を取得します。画面外では未屈折の元画像へ戻さず、天空光に応じた環境色を使います。閉じた洞窟の未確定な光路を明るい空だと決めつけませんが、画面外の遮蔽物を完全に判定する世界空間レイトレーシングではありません。

岸では推定水深に応じて波を弱め、泡を描きます。画面内の深さ推定であり、実際の砕波・泡粒子・水量移動ではありません。透明ブロックは通常のアルファブレンドで重ねますが、複雑な透明物の完全な順序独立描画は行いません。

0.4では、不透明面の直射太陽光成分を別バッファへ保存してから、水による集光に使います。空の拡散光・月・ブロック光や未確定な水底をまとめて強めません。水中では同じ画素の不透明深度と対応する成分を使い、手前の深度書き込み面への漏れを抑えます。屈折の確定解と元の画素の近似は、それぞれ減衰・散乱を適用してから信頼度で混ぜますが、あらゆる段差・画面外の岸を連続にする保証ではありません。

0.5では、局所的な水平水面で屈折した太陽光の水面→水底の光路を求め、水面のFresnel反射損失とRGB減衰を直射成分だけに適用します。従来の水底→視点の減衰とは別で、実シェーダーのテストで両方を確認しました。受光面の元の法線・影は空気中の直射モデルのままなので、任意の水底の向きや曲がった影を完全に再現するものではありません。未確定の水底、離れた池・空洞の水の所属、深度を書かない透明物の材質識別や入射光の散乱は近似・未実装です。浅瀬の青緑色を消すための彩度変更はしていません。

0.6では、水面を上から見る追跡で、深度セル間の反復が飛ばしていた可視水底をサンプル間の交差探索で拾います。既存の手前岸・画面外・水面・残差の拒否条件は残します。太陽円盤は角半径と画素被覆率で光量を正規化し、地形と同じ既存の雨天倍率を一度だけ使います。高い円盤輝度を保存するC0/C4だけを32Fへ変更し、実Irisでも両方の保存面の確保を確認しました。これは限定した直射光の整合性で、雲の空間的な影や水中の一般的な屈折放射輝度まで校正したものではありません。

空は球状大気のRayleigh/Mie単一散乱を数値積分し、毎フレーム1024×512のLUTに保存します。0.3.1では雲を含む空と雲を含まない大気を別バッファへ保存しました。空の補間は経度の継ぎ目と予約行を明示的に扱います。直接太陽光の大気透過率を予約テクセルへ一度だけ計算し、地形・水・光芒で共有します。地表近くの密なエアロゾルを取りこぼさない積分区間を使います。

0.3.2の陸上の霞は、実際のカメラから最初の描画面までの区間だけを積分します。空と同じRGB散乱係数、Beer–Lambert減衰、Rayleigh/Henyey–Greenstein位相関数を使い、各区間の直射光をシャドーマップで遮ります。影範囲外は「日なた」と決めつけず、空気の直射項のみを抑えます。地形の影フォールバック・不透明度・水中光学は変更しません。拡散環境光は雲なしの空の５方向照度から上半球を等方化する近似で、日陰にも残ります。洞窟ではこの環境光を天空光で抑えますが、空気の物理的な減衰と、実際に照らされた入口の散乱まで消しません。密度と雨の倍率は外観上の選択で、実測エアロゾルの校正値ではありません。

雲は1450〜2200 mの曲面を持つ体積層です。3次元密度、視線32区間、光源方向6区間、Beer–Lambert減衰で厚みと内部の遮光を近似します。風・雨天の雲量を描きますが、熱力学や雲の流体計算ではありません。1.1では、地形と水面への直射光はカメラを中心に約500 mの範囲で雲の透過率を8 m間隔で評価し、その外側でカメラ位置の値に滑らかに移行します。多重散乱・大気との結合・地面の環境光・月光は近似、月相は固定満月です。Nether/Endには簡易環境色を使い、地球の太陽・雲を出しません。

影は2048 px・8サンプル、光芒は10ステップが標準です。HDRはRGB共通の柔らかい圧縮で明部の色比と強度の違いを残し、軽い空間フィルターを適用します。夜間は太陽高度に応じた簡易露出補正を使い、夜間倍率を設定できます。近くの灯りへの順応には時間方向の平滑化を使います。現行プレビューは、松明の遮蔽と拡散反射をカメラ周辺に記録したブロック形状に沿って追跡します。反射回数と追跡範囲は有限です。

## 実際の波紋計算

Modは水に触れているプレイヤー・ボートなどの位置と移動を読み取り、最大8接触をシェーダーへ送ります。ブロック・エンティティ・サーバーの物理は変更しません。ネットワーク送信やチャットコマンドも行いません。

GPU上の512×512・64 m四方の持続する高さ/速度場を、2パスの画像ping-pongで更新します。波速2.5 m/s、セル0.125 m、フレームdt上限0.05 s・2分割。2次元波動方程式のCFL値は最大0.5で安定域内です。有限半径の接触力で波が伝播し減衰します。ポーズ中は停止し、カメラ移動時は整数セル分を引き継ぎ、大きなテレポート・水位・ワールド変更時にリセットします。

これは **局所的な線形波高シミュレーション** で、Minecraftの水量・流れ・浮力を置き換えるNavier–Stokesソルバーではありません。同じ高さの壁で隔てられた池には完全な接続判定がなく、流れる水・滝・氷・細かな岸の境界条件も近似です。描画側は選択された水位との差0.30 m以内に制限します。処理落ちでは安定性優先で進行時間を制限します。

## 検証とレビュー

[陸上影の接地修正版](reports/2026-11-20-ground-shadows/README.md)を Aqualumen Lab のシェーダー一覧に追加しました。夕方に石段の影が太陽側に縮むずれを修正しています。既定は通常版0.6です。[2560×1440のゲーム画面から切り出した比較動画](reports/2026-11-20-ground-shadows/ground-shadows-comparison.mp4)

水の開発を保留した[2026-10-23の陸上影プレビュー](reports/2026-10-23-land-shadows/README.md)をLabへ追加しました。通常版0.6を土台に、陸上描画だけの受光面深度補正と4点補間を検証しています。RTX3080Tiの制御26ケースと実Minecraftの各版3場面を確認し、通常設定0.6／physics0.2へ戻しました。候補は未選択です。自然地形・動く太陽・性能とClaudeの最終レビューは未承認で、通常版へは採用していません。

通常プレイ用は上記0.6です。ソースのビルド先は現在、[薄い水の底面の誤判定を修正した0.8.6候補](reports/2026-10-03-thin-water-topology/README.md)です。[0.8.5の水面裏側の修正](reports/2026-10-02-underwater-reasons/README.md)を保持し、浅い底面が波で動くGPU回帰を失敗→成功にしました。本物の水面25ケース・下から見た底面5ケースと、実Irisの5場面も確認しました。通常の高さ範囲・固定バージョンでの限定した修正であり、海岸の色・水中の暗い外周・波で歪む輪郭の自然さは未達です。通常版には採用していません。

```bash
cd /home/kusutohu/repos/aqualumen
make check-development
python3 tools/build.py --development
bash tools/build-physics-mod.sh
```

`make check` は実機GPUで11組の描画シェーダーと3本のcompute shaderをコンパイル・リンクし、実出力でFresnel/全反射/吸収、浅瀬の初期光路、非発光の散乱、空LUTの補間・継ぎ目・予約行、HDR明部の区別、大気透過、波紋の初期化・接触応答・最大dt安定性・整数セル移動・減衰・テレポートリセットを検証します。0.3.1では16/64/128 mの不透明地形への雲漏れと、prepareの2出力を検証しました。0.3.2では実際の合成シェーダーに、拡散環境光と直射キャッシュを固定して前方の空だけを明るくする、影中の局所霞の回帰テストを追加しています。0.3.3では実際の水シェーダーで、画面内外の屈折した空、不透明地形、閉じた洞窟、太陽/月と全反射、カメラ座標の平行移動を検証します。これはMinecraftのFPS測定とは別です。

[実際のClaude Opusレビューと対応](docs/reviews/opus-final-review.md) を保存しました。実際に応答したモデルは `claude-opus-5-5`。設計レビューであり、Opusによる独立したゲーム実行・FPS保証ではありません。

0.3では実際のClaude Sonnet (`claude-sonnet-5-5`) に雲のピクセル角度計算・浅瀬の初期光路・屈折追跡の確定処理の3件を実装してもらいました。[レビュー・修正・検証の区分](docs/reviews/sonnet-v0.3-implementation.md)を保存しています。Codexが生成パッチを修正・適用し、失敗→成功を確認する実GLSLのGPUテストと実際のMinecraft試験を担当します。Sonnet自身がゲーム実行したとは扱いません。

0.3の[検証記録と残る制約](reports/2026-10-01-v0.3.0/VERIFICATION.md)、[主要10場面の実測と画像](reports/2026-10-01-v0.3.0/natural/RESULTS.md)、[ガラス・Nether・End](reports/2026-10-01-v0.3.0/functional/RESULTS.md)、[洞窟](reports/2026-10-01-v0.3.0/cave/RESULTS.md)を保存しています。各場面10秒準備・10秒計測で、主要8場面の平均は162.8〜191.6 FPSでした。Endでは61.46 msの1フレームも記録されており、全場面の最低FPS保証はしません。浅瀬の強い青緑と屈折境界、雲の手続き的な形は改善余地として残っています。

0.2の[実測結果と制限](reports/2026-10-01-v0.2.0/VERIFICATION.md)と[全10場面の生データから再計算した結果](reports/2026-10-01-v0.2.0/natural/RESULTS.md)は旧版に限定した記録です。自然生成の海・岸・川・昼夕夜・雨・水中・視点移動の8場面では平均299.8〜427.0 FPS、各30秒の測定で16.67 ms超は0フレームでした。自動ボート移動では2フレームが超過（最長70.06 ms）したため、全試験を通じた最低60 FPSは未達でした。新しい体積雲の速度をこの旧版の数値から推定してはいけません。

旧0.1.0の[人工平坦ワールドの結果](reports/2026-10-01/RESULTS.md)は旧版に限定した記録です。初回の起動不能は、欠けていた公式Intermediary 1.21.1のJARを検証して補完し、Iris/Sodiumが正常に起動するところまで修復しました。

検証専用Modは、Aqualumen Lab・有効化マーカー・専用ワールドUUID/実際の生成器/seed・統合サーバー・プレイヤーUUIDが一致した場合だけ動きます。測定開始は明示的なローカルファイル要求で、通常利用時には無効です。

```bash
bash tools/build-benchmark-mod.sh
python3 tools/benchmark-control.py --help
python3 tools/report.py <測定runディレクトリ>
```

平均・遅い1%の平均から求めるFPS・p99・最長フレーム・16.67 ms超の数をCSVから再計算して照合します。平均だけから最低60 FPS達成とは判定しません。ロード済み地形と新規チャンク生成中も区別します。

0.3.1の[修正・検証記録](reports/2026-10-02-v0.3.1/VERIFICATION.md)と[実際のSonnet実装協力](docs/reviews/sonnet-v0.3.1-implementation.md)を保存しています。不透明ブロックへの雲漏れは、実GLSLテストの失敗→成功で確認しました。ゲーム内の壁あり・壁なし比較は遮蔽の確認であり、すべての場面の半透明問題が解消した保証ではありません。

0.3.2の[修正・検証記録](reports/2026-10-02-v0.3.2/VERIFICATION.md)、[逆光の旧版](reports/2026-10-02-v0.3.2/before/RESULTS.md)・[新版](reports/2026-10-02-v0.3.2/after/RESULTS.md)、[互換性10場面](reports/2026-10-02-v0.3.2/compatibility/RESULTS.md)、[Codex静的レビュー](docs/reviews/codex-v0.3.2-aerial-review.md)を保存しています。テスト先行で霞の不要な前方光への依存を除き、正当な直射散乱と環境光を残しました。元のユーザー画像そのものを同じ位置・時刻で再撮影した検証ではありません。検証画像の非同期保存も修正し、レポートはPNGの完全性・CRC・寸法・圧縮データを確認します。

0.3.3の[修正・検証記録](reports/2026-10-02-v0.3.3/VERIFICATION.md)、[実際のユーザー視点の修正後画像](reports/2026-10-02-v0.3.3/user-scene/after.png)、[水中3視点の旧版](reports/2026-10-02-v0.3.3/before/RESULTS.md)・[新版](reports/2026-10-02-v0.3.3/after/RESULTS.md)、[互換性10場面](reports/2026-10-02-v0.3.3/compatibility/RESULTS.md)、[Codex静的レビュー](docs/reviews/codex-v0.3.3-underwater-review.md)を保存しています。失敗→成功を確認するテスト先行で、空の四角い切り替わりと視線の座標原点を修正しました。ユーザーのワールドでも同じ位置・向きで確認していますが、時刻・雲は自然に変化しています。検証専用クライアントの終了処理停止は未修正で、通常利用時は検証Modを無効にしています。

0.4の[実装・検証チェックポイント](reports/2026-10-02-v0.4.0/VERIFICATION.md)、[16場面の実測と画像](reports/2026-10-02-v0.4.0/after/RESULTS.md)、[独立した画像・動画の監査](docs/reviews/codex-v0.4.0-visual-audit.md)を保存しています。1440pの各5秒測定では地上・水中の平均約126〜193 FPSですが、夕方と夜に16.67 ms超が各1回あり、最低FPSは保証しません。一部の旧新版比較はフォーカス状態が異なります。1600×900の3本の動画は別の録画負荷下の観察で、1440p性能測定の代わりではありません。浅瀬・ボートの自然さ、空と太陽光の整合性は[継続中の目標](docs/REALISM_GOAL.md)として残っています。今回の実装・監査はCodexで、Claudeの新規呼び出しではありません。

0.5の[実装・検証記録](reports/2026-10-02-v0.5.0/VERIFICATION.md)、[16場面の実画像監査](docs/reviews/codex-v0.5-visual-audit.md)、[通常プレイへの復帰記録](reports/2026-10-02-v0.5.0/ordinary-handoff.json)を保存しています。実機GPUテストと1600×900の互換性・画質確認は通りましたが、これは1440pの新しい性能測定ではありません。岸際の青緑色・鋭い反射/屈折の境界は残っています。0.5の引き渡し時は通常アカウントで新版と専用Modを起動し、元の設定へ戻して一時停止していました。今回もCodexの作業で、Claudeの新規呼び出しではありません。

最新0.6の[実装・検証記録](reports/2026-10-02-v0.6.0/VERIFICATION.md)、[1440pの16場面と生データ](reports/2026-10-02-v0.6.0/real-view/RESULTS.md)、[独立データ監査](reports/2026-10-02-v0.6.0/INDEPENDENT-AUDIT.md)、[実画像の監査](docs/reviews/codex-v0.6-visual-audit.md)、[通常プレイへの復帰記録](reports/2026-10-02-v0.6.0/ordinary-handoff.json)を保存しています。各5秒測定で全16場面のキャプチャ時フォーカスと有効な0.6を確認し、地上・水中・洞窟・ガラスの平均は126.5〜196.9 FPSでした。短い観測区間の数値で、最低FPSや新規チャンク生成中の性能を保証しません。岸の青緑色・鋭い境界と動きの自然さは未達です。検証専用クライアントの終了停止も未修正で、通常利用時には検証Modを無効にし、設定を戻しています。全体の[リアリズム目標](docs/REALISM_GOAL.md)は継続中です。今回の作業と監査はCodexで、Claudeの新規呼び出しではありません。

0.8と専用Mod0.3は[GPU検証済みの候補版](reports/2026-10-02-v0.8.0/WORK-IN-PROGRESS.md)です。実際の局所水深を波の高さと光学法線で共有し、遠方地形に反射が左右されるテストと、可視水底の光が不足する条件を修正しました。深度の補間方式を変えた場合と、水深データがない場合も検証しています。[実ゲームの続報](reports/2026-10-02-v0.8.0-runtime/README.md)では専用TESTワールドで実テクスチャの接続・読み出しを確認し、観測機構のAPI不具合を実Modファイルを使う回帰テストで修正しました。ただし、海岸の強い青緑色と鋭い境界は実画像でも残っており、動きの自然さも未確認です。通常構成は0.6/専用Mod0.2へ戻し、検証用Modを無効にして一時停止しています。

0.8.3では、制御された描画試験で約1.78倍だった水底の直射光の出力を修正しました。[実機6場面の画像・生データ](reports/2026-10-02-v0.8.3/captures/v083-radiance-smoke-20261002-1610/run.json)は1600×900で、平均は海岸約92・川約89・海約66・水中約118 FPSです。1440pや最低FPSの保証ではありません。[実画像監査](reports/2026-10-02-v0.8.3/VISUAL-AUDIT.md)では岸の青緑色・尖った暗帯・雲の形と水中の強い丸まりが残っています。地形/水の名前付き太陽光データ接続と正値キャッシュを[実Iris観測](reports/2026-10-02-v0.8.3/observations/audit.json)で確認しましたが、画質の完成や全光学現象の校正ではありません。通常用の0.6/専用Mod0.2へ戻し、[実際の一時停止画面](reports/2026-10-02-v0.8.3/lifecycle/normal-restored-paused-native-f2.png)まで確認しています。実装・レビューはCodexです。

水中の続報として、[実視点の行列取得と平面の屈折・全反射・反射の検証](reports/2026-10-02-underwater-angular/README.md)を保存しました。実機GPUの平面テストは再実行でも一致しますが、自然な水中の湾曲や暗い外周が直ったという結果ではありません。通常アカウントで専用検証ワールドを起動するとセーブ・終了できることも確認し、TEST名だけの上書きを避ける運用にしています。全体の目標と水の見た目の修正は継続中です。

## 実装の参考

0.8.1は[最初の可視水底を取り逃す条件の修正・検証記録](reports/2026-10-02-v0.8.1/README.md)を持つ開発版です。局所水深を探索開始のヒントに使い、追跡失敗時の近似光路とは分離しました。実際の描画mainを使った失敗→成功、2種類の深度補間、実ゲーム6場面を確認していますが、岸辺の青緑色・尖った暗い帯・雲の形は未達です。[実画像監査](reports/2026-10-02-v0.8.1/VISUAL-AUDIT.md)と短時間1600×900の観測を、画質の完成・1440p性能保証とは区別します。通常用の構成は引き続き0.6／専用Mod0.2です。

- [Irisパイプライン](https://shaders.properties/current/reference/programs/overview/) / [Custom Images](https://shaders.properties/current/reference/buffers/custom_images/)
- [NVIDIA: 波の物理モデル](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)
- [NVIDIA: GPU上の波動方程式](https://developer.nvidia.com/gpugems/gpugems2/part-vi-simulation-and-numerical-algorithms/chapter-44-gpu-framework-solving)
- [NVIDIA: 水底の集光](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)
- [Bruneton: 大気散乱](https://ebruneton.github.io/precomputed_atmospheric_scattering/)
- [PBRT: 有限な媒質区間の光輸送](https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/The_Equation_of_Transfer)
- [PBRT: 媒質の透過率](https://pbr-book.org/4ed/Volume_Scattering/Transmittance) / [Fresnel反射・Snell屈折](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission)
- [PBRT: 3次元格子のDDA走査](https://pbr-book.org/4ed/Volume_Scattering/Media): 各軸の次の格子境界までの距離を更新するアルゴリズムの参考。独自の有限格子・曖昧境界の棄却を使う[最初の水底ソース検証](reports/2026-10-06-water-receiver-main/README.md)は、合成データによる実GPUテストであり、実ゲームの材質・照明連携の完成ではありません。
- [Khronos OpenGL 4.6仕様 §14.6・式14.9](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf): 三角形の属性補間と遠近補正の基準。[実頂点順の面補間](reports/2026-10-06-water-receiver-triangle/README.md)は独自の重心座標実装を保存済みIris頂点コードでGPU照合したもので、実テクスチャ取得・照明連携や自然な水の完成とは別です。
- [同仕様 §§8.14.2–8.14.3](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf): テクスチャ取得とミップ間補間の基準。[実Iris材質・照明入力検証](reports/2026-10-06-water-receiver-light/README.md)は実アトラスの80件の制御付きGPU取得を独立照合したものです。自然な画面微分・実面照明・水表現の完成とは区別しています。
- [NIST DLMF: 不完全ガンマ関数の級数](https://dlmf.nist.gov/8.7.E1)・[連分数](https://dlmf.nist.gov/8.9.E2)・[erfcとの関係](https://dlmf.nist.gov/7.11.E2): TEST用のGaussian条件付きサンプラーのCDF評価。独自実装と[GPU検証記録](reports/2026-10-06-water-conditioned-sampling/README.md)を保持し、少数サンプルの収束・実ゲームの画質合格とは区別します。
- [Mike Giles: 逆誤差関数の近似](https://people.maths.ox.ac.uk/~gilesm/codes/erfinv/): TEST用の逆Gaussian CDFで計算変数の考え方を参考にしました。係数はPythonの分位点から独立に生成し、既存の実装・係数はコピーしていません。[逆CDF・確率座標の積分検証](reports/2026-10-06-water-fast-inverse/README.md)は、通常版への採用や実ゲームの画質合格とは別です。
- [Iris: カメラと描画の座標系](https://shaders.properties/current/how-to/coordinate_spaces/)
- [Microsoft: PCFとテクセルごとの受光面深度補正](https://learn.microsoft.com/en-us/windows/desktop/DxTechArts/cascaded-shadow-maps#calculating-a-per-texel-depth-bias-with-ddx-and-ddy-for-large-pcfs): 陸上影プレビューの考え方の参考。画面微分のコードは使わず、既存の非線形影座標を逆変換して各テクセル中心で受光平面の深度を求める独自実装です。接触硬化や太陽の物理的な半影を再現するものではありません。
- [Khronos: 深度比較サンプラー](https://wikis.khronos.org/opengl/Sampler_Object#Comparison_mode): 既存の比較モードを維持し、陸上影だけで4点の比較結果を補間するための仕様上の参考です。

既存シェーダーパックのコード・有料アセットは使用していません。自作部分はMITライセンスです。
