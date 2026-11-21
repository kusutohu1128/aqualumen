# Leaf light solver: インターフェースと意味論 (file of record)

状態: **IMPLEMENTED (DRAFT-2)**。実装済みの staging ツリーと一致する。実装が仕様と食い違った場合は、このファイルを先に直し、末尾の `Changelog` に記録する。
対象ツリー: `build/leaf-solver/shaders` (基底は `dist/Aqualumen-1.7.0.zip`, SHA-256 `eb760f429d32ea03b87d500a5f7d613a1d9a611794e3b2ddb6dd297ec80d4ec8` の展開)。
成果物 ZIP: `build/Aqualumen-1.8.0-leaf-rc1.zip` (完成時。パスは `solver/status.json`)。

## 0. 不変条件 (プローブが機械的に確認できるもの)

| 項目 | 内容 |
|---|---|
| 新規 image / 設定 | なし。`image.*` は 16 個のまま。`shaders.properties` の設定・スライダーは増やさない |
| `materialId != 10300` | `terrainLight`, `lampLighting`, `lampTransmission` の出力は 1.7.0 と **ビット同一** (葉分岐に入らない) |
| 前面を照らす光 (`dot(n,l) > 0`) | 1.7.0 と同じ式。太陽は `shadowVisibility` と `max(dot(n,sun),0)`、ランプは `p+n*0.025` 起点の `lampVisibility` |
| 既存シグネチャ | `terrainLight` の 4 オーバーロード、`lampLighting` の 4 オーバーロード、`lampTransmission` の 2 オーバーロード、`localSolarTransmission`, `shadowVisibility`, `waterIncidentIrradiance` は変更しない |
| `gl_FragData[1]` (`sunRadiance`) | 前面の直達日射のみ。葉の透過日射は含めない (焦点化する直達経路ではない) |
| `gl_FragData[3]` | `dot(localRadiance+emitted, luma)`。`localRadiance` に葉を透過した **ランプ光は含める** |
| 光源が無いとき | 透過項は 0。環境光・最小値・下駄は足さない (洞窟内の未点灯の葉は 1.7.0 と同じ暗さ) |
| α | `tex.a<0.1` の discard と出力 α は変更しない |

## 1. 材質と面の同定

* 葉 = `mc_Entity.x == 10300` (`block.properties` の既存 ID: acacia/azalea/birch/cherry/dark_oak/flowering_azalea/jungle/mangrove/oak/spruce_leaves)。
* 葉は 1 m の立方体。**可視面の外向き法線は軸平行**であること (`max(abs(n)) > 0.99`)。そうでなければ `LeafSurface.valid=false` でフォールバック (1.7.0 の式)。
* 所有セル (owning voxel) は頂点属性ではなく **位置と法線から導出する** (`at_midBlock` は使わない。プローブの `TerrainRig` は `mc_Entity` しか供給しない)。
  * 法線軸 `a`: `cell[a] = floor(g[a] - 0.5*n[a])` (面は整数平面上にあるので 0.5 の余裕があり、境界上の面でも隣セルを読まない)。
  * 接線軸: `cell[b] = floor(g[b])`。ここで `g = lampGridPosition(position, cameraPosition)`。面の外周 1 mm 程度では隣セルを引き得るが、後述の `start` を所有セル内へクランプするので光路の起点は必ず所有セル内。
  * `valid` は 64 セルのグリッド内であることを要求しない (遠方推定は格子を使わない)。近傍の格子トレースは `leafGridCoverage > 0` (カメラから約 22 m 以内) のときだけ走り、その範囲では所有セルは必ず格子内。

## 2. 放射量の定義 (葉 1 枚の二面ランバート: 反射 ρ、透過 τ)

* `ρ_c = albedo_c` (線形、アトラス × `vertexColor.rgb` の色味。前面の反射は 1.7.0 のまま)。
* 透過率 (チャンネルごと):
  ```
  κ   = LEAF_TRANSMISSION_RATIO = 0.60          // 緑葉の可視域で τ/ρ ≈ 0.5–0.8
  s   = 1 / max(1, (1+κ) * max(ρ_r, ρ_g, ρ_b))  // 明るい花弁でも色相を保ったまま ρ'+τ ≤ 1 に収める
  τ_c = κ * s * ρ_c                              // leafTransmittance(albedo)
  ```
  `ρ'_c = s*ρ_c` とすると `ρ'_c + τ_c = (1+κ) s ρ_c ≤ 1` (吸収 `α_c = 1-ρ'_c-τ_c ≥ 0`)。`τ_c ≤ κ/(1+κ) = 0.375`。
* 背面から入射する放射照度 `E` に対し、可視面からの出射放射輝度は `τ_c * E / π` (ランバート透過)。パックの慣習 (ランプは `albedo * block`、太陽は `albedo * direct/π`) に合わせ、
  * 太陽: `L_sun = τ_c * SOLAR * Tatm * cosB * B * gate * weather / π`
  * ランプ: `L_lamp = τ_c * Σ_i energy_i * cosB_i * vis_i` (`energy_i` と `vis_i` は前面と同じ式)
* `cosB = max(-dot(n, l), 0)` (可視面の法線に対する背面側の余弦)。`n·l ≥ 0` のとき透過項は 0。前面と背面は光源ごとに排他。

## 3. 太陽の幾何モデル (`leafSolarBeam`)

光源方向 `L`: `sun.y > 0` なら `sunDirection()`、そうでなければ `shadowDirection()` (月。放射量は 1.7.0 の月項と同じ)。トレースは 1 フラグメントにつき 1 回。

### 3.1 近傍 (ライトグリッド、64³ セル、1 m)
1. 起点 `q = clamp(g, cell+0.001, cell+0.999)` (面上の点を所有セルの 1 mm 内側へ)。法線入射の弦長は 0.999 m。
2. `q` から `L` 方向へ DDA (最大 64 ステップ、グリッド外で終了)。各セルの `shape = word & 63`:
   * `1` (満タン固体), `3..5` (半ブロック・柵のボックス), `6..9` (ドアのテクスチャマスク) → 光路を閉じる (`B=0`)。丸太・屋根・石はここで必ず止まる。
   * `2` (葉) → `exp(-LEAF_EXTINCTION * 弦長)` を乗じる。`LEAF_EXTINCTION = 1.45 /m` (ランプ経路 `lampTransmission` の定数と同一値)。
   * `16..31` (染色ガラス) → `pow(lampGlass(dye), 弦長)` (RGB)。
   * 所有セルは `word` が 0 でも葉として扱う (強制)。
   * 辺・角の同時横断は `lampCornerClosed` と同じ規則で閉じる。
3. **隠れた内部セル (proxy canopy volume)**: 外面しか描かれない葉塊の内部セルは `lampCellImage` に登録されない。直前のセルが葉 (登録・強制・隠れのいずれか) で、現在のセルが `shape==0` のとき、`leafHiddenCell(cell)` を評価する:
   * 6 方向 (±x, ±y, ±z) それぞれについて `k = 1..LEAF_HIDDEN_REACH(=4)` で最初の `shape != 0` のセルを探し、それが `1` または `2` であれば支持あり。一つでも支持が無ければ隠れセルではない。
   * 隠れセルは葉として弦長を加える。連続が切れたら `leafRun` を終了し、以後のセルには評価しない。
   * 画像・`lampFieldImage` は変更しない (登録語は `lampCellImage` と `lampFieldImage` で 1.7.0 とビット同一のまま)。
4. 最後の葉セルの出口距離 `tTop` を記録する (連続した葉塊の上端)。トレースが葉セル内でグリッド外に出た場合は `tail unknown` とする。
5. 上端の外側にある **グリッド未登録の遮蔽物** (グリッド外・合成シャドウマップだけの屋根) は、`P = q + L*(tTop + δ)`, `δ ∈ {0.25, 1.5}` の 2 点をシャドウマップで判定する (`leafShadowTap`, 4 タップ PCF、1.7.0 の `shadowVisibility` と同じ射影・歪み・バイアス `-0.00015`)。`B *= min(v0, v1)`。`tail unknown` のときは 1。
   * これが「反対側の影面を拾わない」ための要点: シャドウマップは **葉塊の外** でしか参照しない。受光点自身の反対面 (立方体の上面) は決して参照されない。
6. `B_near = trans * tapVisibility`。

### 3.2 遠方 (グリッド被覆外、シャドウマップのみ)
所有セルの出口距離 `t0` (立方体との解析的な交差) の先に 7 点 `δ_k ∈ {0.25, 0.7, 1.4, 2.5, 4.0, 6.5, 10.0}` を置き、`vis_k = leafShadowTap(q + L*(t0+δ_k))`。
```
alive = 1; extra = 0
for k: extra += alive * (δ_k - δ_{k-1}) * (1 - vis_k);  alive *= (1 - vis_k)      // δ_{-1} = 0
B_far = exp(-LEAF_EXTINCTION * (t0 + extra)) * (1 - smoothstep(0.75, 1.0, alive))   // 全点が影なら閉じる
```
遠方では丸太と葉をシャドウマップから区別できない (制限 L1)。

### 3.3 合成
```
c_g = 1 - smoothstep(16, 22, max3(abs(position)))      // leafGridCoverage
B   = mix(B_far, B_near, c_g)
```

### 3.4 ゲート
```
gate    = smoothstep(0, 0.85, lightmap.y) * (1 - 0.85*rainStrength)      // 1.7.0 の直達日射と同じ
```
`gate == 0` ならトレースを行わない。

## 4. ランプの幾何モデル (`lampLighting` の葉オーバーロード)

1.7.0 のループ構造は維持し、ランプ `i` ごとに `nl = dot(n, l_i)`:
* `nl > 0`: 1.7.0 と同一 (`reflectedLamp` / `total` に加算)。
* `nl < 0` かつ `leaf.valid`: 背面。起点 `start = clamp(p, cell+0.001, cell+0.999)` (所有セルの 1 mm 内側。前面の `+n*0.025` は使わない)。`lampVisibility` を `lampTransmissionLeaf` で評価 (所有セル強制葉 + 隠れセル規則 + ステップ上限 48 (前面の既存経路は 32 のまま)、エンティティ遮蔽・ドア・ガラス・角閉鎖は従来どおり)。`transmittedLamp += tint * (11*(level/14)² * strength * falloff * vis / (0.38+d²)) * (-nl)`。
* 光源ごとの遮蔽は互いに独立 (他のランプや太陽の結果を共有しない)。壁が 1 つの光源だけを消し、他は残る。
* ランプの `coverage` (19–24 m のフェード) は透過項にも掛ける。ライトリスト不整合 (`textureSize != 16x512`) のときは 0。
* 手持ち (`carried`) も同じ経路。`carried` は目標セルまで辿る従来規則を維持する。

## 5. GLSL API

```glsl
// lib/leaf_surface.glsl (サンプラ無し。local_lighting.glsl より前に include される)
struct LeafSurface { bool valid; ivec3 cell; vec3 centre; vec3 normal; };
LeafSurface leafSurfaceNone();
LeafSurface leafSurface(int material, vec3 position, vec3 normal);   // §1

// lib/leaf_light.glsl (lighting.glsl が include)
const int   LEAF_MATERIAL = 10300;
const float LEAF_EXTINCTION = 1.45;
const float LEAF_TRANSMISSION_RATIO = 0.60;
const int   LEAF_HIDDEN_REACH = 4;
vec3  leafTransmittance(vec3 albedo);                                     // §2 τ_c
float leafGridCoverage(vec3 position);                                    // §3.3 c_g
vec3  leafSolarBeam(LeafSurface leaf, vec3 position, vec3 lightDir);      // §3, B ∈ [0,1]^3。n·L ≥ 0 のとき 0
float leafShadowTap(vec3 relativePosition);                               // 4 タップ PCF。範囲外・影距離外は 1

// lib/local_lighting.glsl
vec3 lampTransmission(vec3 start, vec3 target, bool carried, inout bool visitedDoor);   // 既存・不変
vec3 lampTransmission(vec3 start, vec3 target, bool carried);                           // 既存・不変
vec3 lampTransmissionLeaf(vec3 start, vec3 target, bool carried, ivec3 leafCell);       // 新規
vec3 lampLighting(vec3 position, vec3 normal, vec3 view, float roughness, float blockLevel,
                  bool water, float bounceConfidence, bool film, LeafSurface leaf,
                  out vec3 reflectedLamp, out vec3 transmittedLamp);                     // 新規 (既存 4 つは leafSurfaceNone() で委譲)

// lib/lighting.glsl
vec3 terrainLight(vec3 albedo, vec3 normal, vec3 position, vec2 lightmap, float ao, sampler2D skyLut,
                  vec3 view, float film, float roughness, LeafSurface leaf,
                  out vec3 sunRadiance, out vec3 localRadiance,
                  out vec3 leafSun, out vec3 leafLamp);       // 新規。戻り値に leafSun+leafLamp を含む
vec3 terrainLight(... leaf, out vec3 sunRadiance, out vec3 localRadiance);               // 新規 (leafSun/leafLamp を捨てる)
// 既存の 4 オーバーロードは leafSurfaceNone() を渡す。
```
`lib/terrain.fsh.glsl` は `leafSurface(int(materialId), worldPosition, normal)` を作って新オーバーロードを呼ぶ。

## 6. プローブ向けの解析的期待値

(`G = SOLAR * Tatm` はプローブが制御する入射量。`c_g=1` の近傍、`gate=1`、無雨)

* 孤立した葉立方体、太陽が真上、下面 (`n=(0,-1,0)`)、他セルは空気、屋根なし:
  `B = exp(-1.45*0.999) = 0.2349` (所有セルの弦長 0.999 m)、`L_sun = τ_c * G * 1 * 0.2346 / π`。前面 (上面) は `ρ * G / π` で 1.7.0 と同じ。
* 真上に葉がもう 1 セル: `B = exp(-2.9)`。真上に石が接する (`cap`): `B = 0` (グリッドで閉じる)。
* グリッドに無い屋根 (シャドウマップの平面だけが 12 m 上): `B ≈ 0` (`leafShadowTap` が 0)。
* ランプ: 面の真後ろ距離 `d` の暖色トーチ、間が空気: `E = tint*energy(d)*exp(-1.45*chord)*cosB` (`chord` は所有セルの弦長。法線入射なら 0.999 m)。2 セル目に葉を置くとさらに `exp(-1.45)` を掛ける。石が間にあれば 0。
* 前面と背面の 2 光源は線形放射輝度で加算。壁は背面側だけを消す。
* 反射 + 透過: `ρ'_c + τ_c ≤ 1` を `albedo` を振って確認できる (`leafTransmittance` は `ρ=1` の白でも `≤ 0.375`)。

## 7. 既知の制限 (実装後に更新)
* L1 遠方 (`c_g<1`) では丸太と葉をシャドウマップで区別できない。丸太 1 m は `exp(-1.45*(t0+extra))` で数 % 漏れ得る。近傍は漏れない。
* L2 多重散乱による樹冠内の拡散光 (深い樹冠の下面の緑の滲み) はモデル化しない。直達ビームと独立なランプ経路のみ。
* L3 隠れセル規則は K=4 以内に 6 方向すべて固体/葉があることを要求するため、厚さ 9 m 超の巨大な樹冠の中心部は空気として扱う (漏れる側)。囲まれた小さな空洞は葉として扱う (暗くなる側)。
* L4 グリッドは ±24 m 付近までで、64 ステップで打ち切る。太陽が水平線近くでグリッドを横切る場合、グリッド外の遮蔽は見ない。
* L5 エンティティ (モブ) は太陽の透過に対して遮蔽しない。ランプの透過は 1.7.0 と同じくエンティティ三角形を考慮する。

## Changelog
* DRAFT-1: 初版。
* DRAFT-2: 実装に合わせて修正。起点を 1 mm 内側へのクランプのみに変更 (旧: 面法線方向に 0.01 / 0.025 m)、`valid` から格子内判定を除外、タップ距離を 0.25 / 1.5 m と遠方 0.25 m 起点に変更、ランプのステップ上限を 48 と明記。コンパイル確認: Mesa llvmpipe 4.5 で全プログラム PASS (`compile-mesa-1.log`)。
