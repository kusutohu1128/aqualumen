# 雪の村と降水境界: 第2シードの実在サイト (2026-11-21)

照明スコアの追加ではなく、**次に実際に歩ける場所**を決める調査。Minecraft クライアント・Iris・GPU・Lab・既存ワールドには一切触れていない。`shaders/` と `release/` は読み取りのみ。生成したリージョンファイルは `/tmp` にだけあり、リポジトリには入れていない(配布不可)。

機械可読な要約: [`site-receipt.json`](site-receipt.json)。詳細: [`site/analysis.json`](site/analysis.json)(68ピース全部・全住居の照合)、[`site/transect.json`](site/transect.json)(131列のバイオーム)、[`site/house-layers.txt`](site/house-layers.txt)(家の実ブロック断面)、[`site/precipitation-map.png`](site/precipitation-map.png)(白=雪、青=雨、赤枠=村ピース、黄=選んだ家)。

## 1. 結論

| 項目 | 値 |
| --- | --- |
| シード | **20261139**(Lab の既存ワールド AqualumenNaturalV2 は 308060 なので第2シード) |
| 生成元 | バニラ 1.21.1 (world_version 3955)。Prism が持つ Mojang `client.jar`(sha1 `30c73b1c…9def88`、Mojang メタと一致)の `net.minecraft.server.Main` を、127.0.0.1・オフライン・CPUのみで起動 |
| 村 | `minecraft:village_snowy`、68ピース、BB `(-940,64,515)–(-867,91,619)`、中心 `snowy_meeting_point_3` = **(-912, 67, 576)**。ワールドスポーン (-64,66,-48) から約1050ブロック |
| 家 | ピース20 `snowy_small_house_7`、`CLOCKWISE_90`、BB `(-905,69,575)–(-899,75,580)`。Mojang のテンプレートを同じ回転・位置で置いた BB と一致。テンプレートの非空気セルの **94.2%** が保存チャンクのブロックと一致。残りは「テンプレートでは空気→雪レイヤー14、トウヒの葉3」だけ(構造物生成後の自然雪と木) |
| 扉 | `spruce_door` 下半分 **(-902, 70, 576)**。外側は北(z 減少側)、内側は南 |
| 壁 | 扉の両隣 (-901,70,576) と (-903,70,576) は `stripped_spruce_log`。窓: `glass_pane` (-902,71,579) |
| 室内の床 | **(-902, 69, 578)** `stripped_spruce_log`、上2マスは空気。立つ足元ブロックは (-902,70,578)。白いベッド同居 |
| 屋根 | 床の真上: y73 `lantern`、y74 `spruce_planks`、y75 `spruce_slab`(bottom)。屋根の頂 y=75。稜線には露出した下付き `spruce_slab`(z=575,577,578,580)があり、数か所だけ雪レイヤーが載る([`site/house-layers.txt`](site/house-layers.txt)) |
| 外の開けた地面 | (-902, 69, 570) `farmland`(ジャガイモ)、バイオーム snowy_plains |
| 雪 | 生成済み 289 チャンクのうち、雪クラス列 3210 のうち 2698 に雪レイヤー/雪ブロック。雨クラス列 854 のうち雪が載ったのは 2 だけ(境界付近の4ブロック格子と実バイオームの差と見ている) |
| 近くの雨地点 | 平原 (plains、気温 0.8) が西側。扉から西南西へ約 **101 ブロック**。雪→雨の切り替えは (x=-1003) → (x=-1007) の4ブロック幅 |

雪の村と雨の平原が **同じ嵐の下で隣り合う**。村の中心は雪(snowy_plains、気温 0.0、`has_precipitation`)、西の平原は雨(plains、気温 0.8)。どちらも標高 y≤80 なので高さによる気温補正は入らない。

## 2. 選定手順(事前に決めた規則、手選びではない)

規則: シードを 20261121 から順に試し、(1) `/locate structure minecraft:village_snowy` が原点から1500ブロック以内、(2) その村から `/locate biome` の最短の雨クラスのバイオーム(taiga・forest・plains・birch_forest・flower_forest・old_growth_*・meadow・sunflower_plains・dark_forest)が260ブロック以内、を最初に満たしたものを採る。`locate biome` の刻みは32ブロックで粗い。

- 20261121–20261132(12個): 該当なし。1500以内に村があったのは 20261123(雨まで497)、20261124(273)、20261129(346)。20261124 は260に13ブロック足りず不採用。ログ: [`screen-batch1.log`](screen-batch1.log)
- 20261133–20261139(7個): **20261139 が19個目で成立**(村 (-912,576)、最寄りの plains まで135)。20261137 は 303 で不採用。ログ: [`screen-batch2.log`](screen-batch2.log)

最初の12個で規則を満たすものが無かったため、同じ規則のまま追加で走査した。規則や閾値は変えていない。1シードあたり約15秒。

## 3. 検証した内容と、していない内容

検証済み(保存された chunk NBT と Mojang の jar だけから):

- 構造開始 `structures.starts["minecraft:village_snowy"]` が存在し、`Children` に68ピースがある(街路・街灯・住居・農地)。
- 4軒の住居ピースを、jar 内の `data/minecraft/structure/village/snowy/houses/*.nbt` に同じ回転・原点を適用して照合した。BB 一致、ブロック一致率は `snowy_small_house_1` が **100%**(ピース57)、`small_house_7` が 94.2%、`small_house_5` が 86.7%、`small_house_8` が 76.4%。不一致はすべて「テンプレート空気→雪/草/葉」で、構造後の地物。[`site/analysis.json`](site/analysis.json) の `houses_checked`。
- 選んだ家は、扉・室内の床・屋根・壁・窓がテンプレートと保存ブロックの両方で確認できる。サーバー側でも `execute if block -902 70 576 minecraft:spruce_door` が真になった。
- 境界: 扉から (-1006,594) までと、その先24ブロックの直線 131列で、本物のゲームの1ブロック単位のバイオーム検索(`execute if biome`)を **y=70 と y=67** で7バイオーム分問い合わせた。129列は1つのバイオームに確定。雪クラスから雨クラスへの切り替えは1回だけ。**x=-1004 と -1005 は高さで答えが違う**(y=67 は plains、y=70 は snowy_plains)ので足元の候補から外す。

未検証(推定・導出に留まる):

- **クライアントも Iris も起動していない**。`biome_precipitation` が各立ち位置で 1 か 2 になる値は、Iris 1.8.8 のバイトコードとバイオーム JSON からの導出であり、実クライアントで読んだ値ではない。
- 降水クラスは「`has_precipitation` かつ気温 <0.15 なら雪、それ以外は雨」という規則を JSON の値に当てた。エンジン自身の `Biome.getPrecipitationAt` を呼んだわけではない(第6節の否定的結果)。
- 4ブロック格子の面積調査はセル単位で、境界付近は1ブロック単位とずれる。1ブロック単位は上の131列だけ。
- y>80 の列(氷の棘、4624セル中560)は気温が高さに依存するため未解決のまま。
- 同じシードを別々に2回生成した比較で、**村ピース68個の BB・回転・位置と家の全テンプレートセルの内容ハッシュは完全一致**した(`ef8c1c1a…ab2b`)。一方、地表の飾り(短い草か雪レイヤーか)が 73,984 列中 **86 列**違った。村の BB 内には0列、家からは73ブロック以上離れている。つまり村・家は再現できるが、地表の草/雪の細部はビット単位では再現しない。

## 4. 再現手順

作業ディレクトリは毎回新しい `/tmp` に作られる。CPU は `nice 15` と `taskset`(4コア)、JVM は `-Xmx2G -XX:+UseSerialGC -XX:ActiveProcessorCount=4 -Dmax.bg.threads=3`。サーバーは必ず `stop` で止めており、終了コードは全て0。

```
cd reports/2026-11-21-settlement-light/tools
python3 -I screen_seeds.py 20261121 19                      # 約5分。20261139 で停止
python3 -I gen_site.py 20261139 -912 576 -1008 672 4-7      # 289チャンクを約23秒で生成。WORLD の /tmp パスを出力
python3 -I analyze_site.py WORLD ../site                    # 村・家・降水地図
python3 -I transect_probe.py WORLD ../site/analysis.json ../site/transect.json 8-11
python3 -I make_receipt.py                                  # ../site-receipt.json
```

道具は標準ライブラリのみ (`mcnbt.py` が NBT と Anvil を読む)。`vserver.py` の SHA-256 などは receipt の `tool_sha256` に記録。**注意**: サーバーの起動には `eula.txt` が必要で、`eula=true` を使い捨ての `/tmp` ディレクトリ内にだけ書いた。これは Mojang EULA への同意にあたるので、方針上気になる場合は知っておいてほしい。起動時に oshi の `NoClassDefFoundError` 警告が出るが、ハードウェア情報の取得だけで無害(クライアント専用ライブラリを除外したため)。

## 5. 実際に歩く道

1. Lab に、**新しい**バニラのワールドをシード `20261139`、構造物あり、ピースフル、チートありで作る(既存ワールドは使わない。ワールド作成は Lab の操作なので、起動担当が行う)。
2. 村へは `/tp @s -902 70 570`(家の北、開けた畑)。歩くならスポーン (-64,66,-48) から `/locate structure minecraft:village_snowy`。村は南西へ約1050ブロック。
3. 家: 扉 (-902,70,576) から入り、室内の床 (-902,70,578) に立つ。屋根は真上 y74–75。
4. 境界へ: 扉から西南西へ約101ブロック。足元の候補は receipt の `boundary.stand_points`(足元ブロック): 雪側 (-996,67,592) と (-1003,68,593)、雨側 (-1007,68,594) と (-1014,69,595)。
5. 各立ち位置で F3 の `Biome:` 表示を読み、足元が `snowy_plains` か `plains` かを記録する。

家のブロックの確認は `/execute if block -902 70 576 minecraft:spruce_door`、床は `/execute if block -902 69 578 minecraft:stripped_spruce_log`(上の再現性の注記どおり、村と家は確定、地表の草/雪は数列違う可能性)。

## 6. 否定的結果(証拠として使っていない)

[`tools/negative/`](tools/negative/) に残した。**プレイヤーのいないサーバーでは、強制読込みチャンクはランダムティックもエンティティの更新もされない。**

- `weather-accumulation-NEGATIVE.json`: 降雨・積雪上限8・2400ティックを進めても、雪の増加は雪クラス・雨クラスとも0列。ワールド時間は進んだのにチャンクの `InhabitedTime` が 0 のままで、チャンクが更新されていなかった。
- `rain-fire-probe-NEGATIVE.json`: 燃える無敵のブタで `isRainingAt` を試す案。晴天でも20ティック後に `@e` から消えるので比較不能。世界スポーンの読込み半径を広げても同じ。

雨/雪のエンジンによる直接の確認には、実際のプレイヤー(クライアント)が必要。今回は行っていない。

## 7. 天候シェーダー: 観察者の降水か、面の降水か (1.8.0 のソース、読み取りのみ)

**結論: 地面・屋根・水面の濡れは「プレイヤーの足元ブロックのバイオーム」で決まり、降る粒子は「その列のバイオーム」で決まる。境界ではこの2つが食い違う。**

### Iris 1.8.8 の入力 (Lab の `iris-fabric-1.8.8+mc1.21.1.jar`、sha256 `b5ad39a6…92f5`)

`net.irisshaders.iris.uniforms.BiomeUniforms` のバイトコードを `javap` で読んだ(新しい空ディレクトリに該当クラスだけ展開):

- `biome_precipitation`: `PER_TICK` の整数ユニフォーム。`playerI(...)` が `LocalPlayer.blockPosition()`(`method_24515`)で `Level.getBiome` を引き、`Biome.getPrecipitationAt(BlockPos)`(`method_48162`)の列挙型を **NONE→0、RAIN→1、SNOW→2** に変える。カメラ位置ではなくプレイヤーの足元ブロック。
- `rainStrength`: `CommonUniforms.getRainStrength()` = `level.getRainLevel(tickDelta)` を 0~1 に制限。**バイオームを見ない全世界共通値**。
- `wetness`: 同じ値を `SmoothedFloat` で平滑化。やはり全世界共通。

### パックの使い方

| 場所 | 入力 | 意味 |
| --- | --- | --- |
| `release/shaders/lib/rain_surface.glsl:14` | `wetness<=0.001 \|\| n.y<0.95 \|\| biome_precipitation!=1 …` なら濡れなし | 上向きの面の水膜。**観察者のバイオームが雨でなければ、視界内の全面で水膜が出ない** |
| 同 `:17` | `clamp(wetness)*rainExposure(...)` | 全世界共通の濡れ × 屋根下の遮蔽 |
| `release/shaders/lib/rain_material.glsl:5-12` | ブロックID→(散乱、粗さ、水膜率) | 10301(下付き `spruce_slab`)・10602(`spruce_planks`)・10002(`grass_block`)などは水膜あり。**`snow`・`stripped_spruce_log`・`farmland` は表になく水膜なし** |
| `release/shaders/gbuffers_water.fsh:248` | `biome_precipitation==1` で雨のさざ波 | 水面の雨の波も観察者基準 |
| `release/shaders/gbuffers_weather.fsh:20,36` | テクスチャの青−赤で `liquid`(雨か雪か)、`1-0.85*rainStrength`(全世界共通) | **観察者のバイオームを使わない**。雨筋か雪片かはバニラが列ごとに描き分けた粒子のテクスチャで決まる(バニラの `renderSnowAndRain` が列ごとに降水種別を見ることは、今回は未確認の既知知識) |
| `release/shaders/lib/weather_light.glsl:37` | `liquid` で雨・雪の位相関数を混合 | 同上。バイオームは見ない |

### 読んで予想される不整合(未実測)

1. **観察者が雨側にいる**と、雪の村の屋根の `spruce_slab`/`spruce_planks`・石の面は濡れて見える。そこで降っているのは雪。
2. **観察者が雪側にいる**と、西の平原の `grass_block` は雨が降っていても水膜が出ない。そこでは雨筋は描かれる。
3. 境界をまたぐと `biome_precipitation` が1tickで 2↔1 に変わり、`wetness` は高いまま。**視界内の全ての水膜が1フレームで出入りする**(平滑化されない硬いゲート)。
4. 雪レイヤーのブロックは材質表にないため、雪の地面は両側で濡れない。これは意図に近い。
5. 全世界共通の `rainStrength` による太陽・雲・霧の減光は、バニラの雨量が世界共通であることと整合する。

## 8. 提案テスト: 境界の両側、同じカメラ向き、同じ面

目的: 水膜が「観察者」に結び付いているのか「面」に結び付いているのかを分ける。シェーダーは編集しない。診断に水膜の値が必要なら、1.8.0 とは別の診断用コピーで行う(rain-eaves の `measured.json`/`plan.json` と同じ、既知ブロックを投影して11×11画素を測る方式)。

準備: 第5節のワールド、`/gamerule doWeatherCycle false`、`/time set 6000`、`/weather rain`。`wetness` が飽和する(rain-eaves の実測で 25秒 約0.93)まで **少なくとも40秒**待つ。ベンチマークMod は無効のまま(通常ワールド)。

立ち位置(足元ブロック、receipt の `stand_points`): 雪側 **S1 (-996,67,592)**、**S2 (-1003,68,593)**、雨側 **R1 (-1007,68,594)**、**R2 (-1014,69,595)**。S2 と R1 は4ブロックしか離れていない。到着後 F3 の `Biome:` が S は `snowy_plains`、R は `plains` であることを確認して記録する。

向きは2つ、各立ち位置で同じ yaw/pitch、ピッチは水平:

- **東向き (yaw 270)**: 雪の村の家の屋根(`spruce_slab` y=75、x=-902、z=575~580。観察距離は約95~112ブロック)と近い雪の家。雪列の面。
- **西向き (yaw 90)**: 平原の `grass_block` の上面(x≈-1020~-1060、観察距離 約10~60ブロック)。雨列の面。

測るもの: 各向き・各立ち位置で、既知ブロック上面の同じワールド座標の画素パッチ(表示輝度と、診断コピーなら水膜率)。立ち位置は4~11ブロックずれるだけで、遠い面の視差は小さい。パッチを再投影して合わせる。

| 面 \ 観察者 | 雪側 S1,S2 | 雨側 R1,R2 | 面を基準にした期待(バニラの降水) | 現行1.8.0のコード上の予想 |
| --- | --- | --- | --- | --- |
| 雪の村の屋根(東向き) | 乾く | 濡れる | S も R も乾く | **R で濡れる**(観察者基準) |
| 平原の草(西向き) | 乾く | 濡れる | S も R も濡れる | **S で乾く**(観察者基準) |

判定の分け方: 2つの面の水膜の変化が **同符号**(S→R で両方濡れ側に動く)なら観察者結合。屋根は両側で乾いたまま、草は両側で濡れたままなら面基準で正しい。1.8.0 は前者になるはず。

境界の硬さ: S2 から R1 へ60 fps で歩いて渡る(約0.5秒)。画素パッチの時系列で、`wetness` の約6秒の指数的な立ち上がりではなく**約1tick(50 ms)の階段**になれば第7節3の予想どおり。逆に往復して R1→S2 で同じ階段が消える側にも出るか確認する。

外れ値の扱い: x=-1004,-1005 は高さによってバイオームが違うので、この2列は立ち位置にしない。y>80 では気温の高さ補正が入るので、この試験は y≤80 で行う。

### 直す場合の候補(今回は実装しない)

- 列ごとの降水種別を持つ情報源: (a) `gbuffers_weather` は半径 約10ブロックまでバニラの列別の答えを粒子として得ているが、全面は覆えない。(b) 既存の読み取り専用の `physics-mod` が、カメラ周囲 256×256 の列ごとに `Biome.getPrecipitationAt` を引いて 1 画像に書き、現在の雨よけ画像と並べて参照する。(c) 草や葉は頂点色(バイオームのカラーマップ)から冷たさを推定できるが、石や木には使えない。

## 9. 補足

- 同じ report ディレクトリに、別の担当が作った `playable/` がある。こちらは触っていない。
- 開発中に止め損ねたサーバー2つ(スクリプトの例外で孤児化)は、Java の終了フック(SIGTERM)で保存して停止させた。成果物には使っていない。
- 後始末: 試験用のコピーや再生成したワールドは削除済み。残したのは `/tmp/aql-settlement-world-20261139-cy46ceo0`(15 MB、生成した本体。再生成で復元可能、配布不可)のみ。バックグラウンドのサーバー、Java プロセスは残っていない。
