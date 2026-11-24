# 1.8.0 の機能詳細

`../dist/` のリンクはローカルのビルド出力です。配布物は [Releases](https://github.com/kusutohu1128/aqualumen/releases) から入手できます。

- [シェーダー 1.8.0](../dist/Aqualumen-1.8.0.zip) を `shaderpacks/` に、[接触波紋用Mod 0.2.0](../dist/aqualumen-physics-0.2.0.jar) を `mods/` に入れます。対応環境は Java 21、Fabric、Iris 1.8.8、Sodium 0.6.9 です。
- 標準設定は `BALANCED`。遠近の影と水面を2560×1440・描画12チャンクで検証しています。以前の水の見え方に戻したいときは、Labに残してある `Aqualumen-0.6.0.zip` を選べます。
- [1.0.1との実ゲーム比較](../reports/2026-11-20-shore-light/comparison.jpg)、[同じ岸で見たPhoton・Complementaryとの違い](../reports/2026-11-20-shore-light/reference-comparison.jpg)、[動画・条件別のフレーム時間](../reports/2026-11-20-shore-light/README.md)を確認できます。

1.8.0 では、太陽や松明に背を向けた葉にも光が届きます。可視面の位置から葉の厚みと光源までの経路を求め、途中に幹、石壁、扉があればその光を遮ります。白い壁の前に葉と松明を置くと、壁に葉の隙間を通った光が映ります。ゲームのアトラスから葉の模様と色を読み、バイオームの色を合わせます。連なった樹冠の内側は平均的な減衰で近似しています。

同じ白樺の木陰で、松明を置くと幹の側面に暖色が入り、魂の松明に替えると青みが増します。葉越しの光は、炎の見かけの大きさに応じて影の縁がぼけます。RTX 3080 Ti、2560×1440、12チャンクのこの視点では、各10秒の平均は消灯49.6、松明31.3、魂の松明32.2 FPSでした。[木陰で点灯・消灯した実画面](../reports/2026-11-21-leaf-light/timing-cone-daylight.jpg) · [白壁に落ちる葉の影の拡大](../reports/2026-11-21-leaf-light/penumbra/cone-wall.jpg) · [オーク・シラカバ・サクラの違い](../reports/2026-11-21-leaf-light/projected/cone-species.jpg)

葉の表と裏を別々に扱う考え方、色ごとの吸収・散乱、実際のゲーム画面の見え方を参考にしました。Aqualumen の透過率は Minecraft のテクスチャとブロック寸法に合わせた近似値です。[Habel らの葉の透過光モデル](https://www.cg.tuwien.ac.at/research/publications/2007/Habel_2007_RTT/) · [Jacquemoud と Baret の PROSPECT](https://www.sciencedirect.com/science/article/pii/003442579090100Z) · [Photon v1.1](https://modrinth.com/shader/photon-shader/version/6FdrBtKp)

雨の夜にランタンの下を歩くと、濡れた石に橙色の照り返しが伸びます。乾いた軒下には石そのものの質感が残り、魂のランタンに替えると近くを落ちる雨にも青い光が届きます。木の下では太陽の光と松明の光を別々に計算します。松明を外して戻すと、樹冠が落とす日の影を保ちながら、炎の届く幹や草の色が変わります。[木陰の松明を点けた実画像](../reports/2026-11-21-door-light/birch.jpg) · [軒先の旧版と新版](../reports/2026-11-21-rain-eaves/fixture/eaves-comparison.jpg) · [雨粒と水膜の検証](../reports/2026-11-21-rain-eaves/README.md)

水膜では材質ごとの吸水と粗さを考慮し、GGXの微小面モデルで石に映る光の幅を求めます。雨粒では入射方向と視線のなす角に応じて光を散乱させます。Photonの降雨時の材質・天空光の条件を参照し、屋根の高さと光源までの遮蔽はAqualumen側で計算します。[濡れた表面の研究](https://doi.org/10.2312/EGWR/EGWR99/273-282) · [PBRTの微小面モデル](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory) · [PBRTの散乱位相関数](https://pbr-book.org/4ed/Volume_Scattering/Phase_Functions) · [Photonの降雨処理](https://github.com/sixthsurge/photon/blob/main/shaders/include/surface/rain_puddles.glsl)

夕暮れの家でダークオークの扉を閉めると、隣室のランタンから床へ差し込んでいた暖色が引きます。オークの扉は上部の四つの小窓から、アカシアの扉は細い格子の間から光を通します。ゲームが使う扉のテクスチャと厚さを読み、ランタンの発光面から各隙間を見通せる割合で、壁に落ちる光の縁をぼかします。[ゲーム内の扉による投影](../reports/2026-11-21-door-light/window/shipped-projection.jpg) · [半影の拡大比較](../reports/2026-11-21-door-light/window/shipped-edge-comparison.jpg) · [面光源の積分の参考文献（PBRT）](https://pbr-book.org/4ed/Light_Sources/Area_Lights)

松明と魂の松明を両手に持つと、岩に暖色と青い光が同時に届きます。手ぶらに戻せば元の暗さに戻ります。露出は目の前の面に実際に届いた光に応じて変化し、地上が正午でも、閉じた廃坑では暗所に順応します。[森の昼と夜](../reports/2026-11-21-carried-light/polished-forest.jpg) · [廃坑の両手比較](../reports/2026-11-21-carried-light/polished-mine.jpg) · [検証記録](../reports/2026-11-21-carried-light/README.md)

柱の陰でランタンが直接見えない白壁にも、近くの赤いコンクリートで反射した光が届きます。赤壁を磨かれた深層岩に替えると白壁の赤みが弱まり、二面の間に石の仕切りを立てると反射光が遮られます。反射の計算にはゲームが描くブロックのテクスチャを使います。対象は近くの不透明な立方体の面で、光源からの拡散反射を一回まで追います。「光」の設定から「松明・ランタンの間接光」を切り替えられます。[1.6.0で木陰の松明を点けた実画像](../reports/2026-11-21-door-light/birch.jpg) · [反射光の検証記録](../reports/2026-11-21-indirect-light/README.md) · [光輸送方程式](https://pbr-book.org/4ed/Light_Transport_I_Surface_Reflection/The_Light_Transport_Equation)

1.4プレビューで導入した、生き物が局所光に落とす影も通常版に含みます。牛の頭・胴・脚が光を遮り、小麦を追って歩くと影も壁の上を移動します。[1.4.0 プレビュー](../dist/Aqualumen-1.4.0-preview.1.zip) · [実ゲーム動画](../reports/2026-11-21-mob-light/living-walk/wheat-follow.mp4) · [通常版との比較](../reports/2026-11-21-mob-light/README.md)

暗いオークの幹の前で灯りを取り出し、洞窟へ下りて水辺へ戻るところを、同じ道で二度撮影しました。[夕暮れの松明・41秒](../reports/2026-11-21-continuous-walk/dusk-walk-final/walk.mp4) · [雨の夜のランタン・29秒](../reports/2026-11-21-continuous-walk/rain-bank/walk.mp4)

松明・ランタン・焚き火・シーランタンなどはブロックの位置と発光状態から取得します。太陽、月、複数の設置光源の照度を面ごとに加算します。松明には近距離で発散しない逆二乗減衰を使い、葉は通過距離に応じて減光します。色付きガラスの透過色と炎の色は演出用の近似です。光源の周囲14ブロックを計算し、8ブロック四方の各立方体で最大12灯を選びます。視点から19〜24ブロックで通常のブロック光へ移行します。松明を置いていない場所でも、溶岩や未登録の発光ブロックには従来の照明が効きます。[点光源と距離減衰（PBRT）](https://www.pbr-book.org/4ed/Light_Sources/Point_Lights) · [Irisのブロック発光属性](https://shaders.properties/current/reference/attributes/at_midblock/) · [比較したPhotonの照明設定](https://github.com/sixthsurge/photon/blob/main/shaders/shaders.properties)

夜に松明のある部屋に入ると、壁に届いた光に合わせて露出が落ち着きます。暗がりへ戻るとゆっくり回復します。炎のごく近くには淡い光のにじみが現れます。Irisのシェーダー設定から、夜の露出順応と光源のにじみを個別に調整できます。[実際の森での点灯比較](../reports/2026-11-20-local-light/forest-final.jpg) · [石壁・色ガラス・複数光源](../reports/2026-11-20-local-light/placed-lights-final.jpg) · [動画と実測結果](../reports/2026-11-20-local-light/README.md) · [眼内散乱によるグレアの参考文献](https://www.graphics.cornell.edu/pubs/1995/SSZG95.pdf)

水深3.25 mから見上げた1.0.1では、波と雲が重なって生じる細い縞の明暗を、一画素が受ける光の量に合わせて和らげています。[1.0.0との実ゲーム比較](../reports/2026-11-20-underwater-refinement/comparison.jpg) · [検証条件と動画](../reports/2026-11-20-underwater-refinement/README.md) · [微小な面における反射・屈折の参考文献（PBRT）](https://pbr-book.org/4ed/Reflection_Models/Rough_Dielectric_BSDF)

水中で見上げたとき、カメラから隠れた岸は、影を描く際に得た周囲32×24×32ブロックの実際の面と交差判定します。砂と砂利が濡れたときの散乱低下には二流束モデルを採用しました。表面の波紋には、雨粒が水に当たって広がる短い重力・表面張力波も加えています。 浅瀬の泡は、波が浅い水底に乗り上げて崩れる条件で現れます。草岸や石段のそばでは、近くの地形が遮る空の光を画面の深度から推定します。[濡れた材質の光学モデル](https://doi.org/10.2312/egwr/egwr99/273-282) · [地平角による環境遮蔽](https://developer.download.nvidia.com/presentations/2008/SIGGRAPH/HBAO_SIG08b.pdf) · [Irisのカスタム画像](https://shaders.properties/current/reference/buffers/custom_images/) · [外観の比較に用いたPhoton](https://modrinth.com/shader/photon-shader/version/6FdrBtKp) · [Complementary Unbound](https://modrinth.com/shader/complementary-unbound/version/Z1zqMzjh)

水面では波の傾きから屈折・Fresnel反射・全反射を計算します。カメラから隠れた砂底を探すため、影を描くときに実際に見えた地形の位置・材質・照明を記録し、屈折した光線が横切る順にブロックと交差させます。浅い水では水底までの距離に応じて光が減衰し、水底で跳ね返った日光が水中の段差を照らします。影の視点からも隠れた地形・植物は近似になります。太陽は見かけの直径を約0.53度に保ち、大気の前方散乱によってその周囲を明るくしています。[Irisのシャドウ描画](https://shaders.properties/current/reference/programs/shadow/) · [Irisのカラー添付](https://shaders.properties/current/reference/buffers/shadowcolor/) · [PBRTの誘電体境界](https://pbr-book.org/4ed/Reflection_Models/Dielectric_BSDF)

通常版のGLSLは [release/shaders](../release/shaders) にあります。リポジトリのルートで `python3 tools/build.py` を実行すると同じZIPを生成します。`make check` は通常版の描画プログラムをコンパイル・リンクし、波紋のcompute更新、屈折、吸収、大気と遮蔽をGPUで検査します。開発中の別系統は [shaders](../shaders) にあり、ビルドは `python3 tools/build.py --development`、検査は `make check-development` です。
