# entity-light-21 — 設置光・手持ち光による動くエンティティの影（候補）

対象: Iris 1.8.8 / Minecraft 1.21.1。`release/shaders` に対する候補。Minecraft は起動しておらず、何もインストールしていない。コミットもしていない。

## 方式（幾何ベース、GPU のみ）
1. **捕捉** `shadow_entities.vsh/.gsh/.fsh`。Iris は影パスのエンティティ描画をこのプログラムに送る（ビーコン光線・テキスト・雷も同じプログラムに来る）。GS は三角形をそのまま出力し、同時にアニメーション済みの実三角形をカメラ相対 m 単位で `aqualumenEntityTriangles` に保存する（v0, e1, e2）。
   - 区間: ±24 m × 0.5 m セル（96³）、2 m ブリック占有ビット。この範囲は `lampLighting` の受光点と光源の両方の有効範囲（19–24 m でフェード）と一致する。両端が箱の内側にある線分は箱から出ないため、格子端で影が飛ぶ（ポップ）ことはなく、端のフェードは既存の 19–24 m フェードがそのまま担う。
   - 挿入: 支配軸に沿った列ごとの平面範囲と SAT による三角形/箱判定（保守側）。`imageAtomicExchange` でセル単位の連結リストを作る。ノードには 16 bit 固定小数点の包囲球と self ビットを持たせる。
   - アルファ切り抜き: 三角形ごとに 8×8 のサブ三角形格子（64 bit）を `gtexture` から作る。頂点 α < 0.1 は捨てる。
   - フィルタ: `entity.properties` の 21000（モブ・プレイヤー・防具立て・乗り物）と 21001（`minecraft:current_player`）だけを保存する。name_tag / entity_flame / entity_shadow / 投射物 / アイテム / 額縁・絵画 / ディスプレイ / 雷 / エンドクリスタル、および ID 0/−1（ビーコン光線・看板文字など）は保存しない。
2. **再構築** `clear=true` の heads/meta は Iris が毎フレーム影パス前に消去する（`IrisRenderingPipeline.beginLevelRendering` で確認）。triangle/node は消去しないが、当フレームの heads からしか辿れない。このため移動・デスポーン・再センタリングで影が残らない。
3. **判定** `lib/entity_occlusion.glsl`: 受光点→光源サンプルの線分ごとに、全体 AABB でのクリップ → 2 m ブリック DDA（空ブリックは 1 フェッチ）→ 0.5 m セル DDA → 包囲球で棄却 → Möller–Trumbore（両面、any-hit）→ 切り抜きマスク、の順で判定する。両端 1 cm を除外するので、受光点の背後や光源の先にあるものは無視される。手持ち光（carried）と一人称の手（gbuffers_hand）では self 三角形を無視する。
4. **ソフトシャドウ** 既存の `LOCAL_LIGHT_SAMPLES=3` の発光円盤 3 タップに、ブロックの透過率とエンティティの可視性をタップごとの積として統合した（`lampSample`）。
5. **上限** 1 サンプルあたり 160 三角形テスト。1 シェーディング点あたり 512 work 単位（ブリック手順・セル訪問・三角形テストの合計）。上限を超えたら、その線分はエンティティの影なしとして扱う。光源リストは強い順に並ぶので、超えると弱い光源の影から欠ける。ただし shadowcomp1 は手持ち光をリストの末尾に置くため、混雑時は手持ち光の影が先に欠ける。
6. 太陽影マップと shadowcolor0/1 の出力は従来の `shadow` フォールバックと同じ（`shadow_fsh.glsl` を共有し、名前だけ #define で付け替え）。地形プログラムには GS を追加していない。オプション `ENTITY_LIGHT_SHADOWS`（既定 1、0 にすると捕捉も判定も外れる）。

## 成果物
- `entity-light-21.patch` — リポジトリのルートで `git apply build/entity-light-21/entity-light-21.patch`（`patch -p1` でも可）。`git apply --check` と `patch --dry-run` が通り、スクラッチ上の release コピーに適用した結果が `shaders/` と完全一致することを確認済み。土台は `base-sha256.txt`。作業中に release/ が並行して更新された（01:37、手持ち光の DYNAMIC_MESH 等）ため、その最新版にリベース済み。
- `shaders/` 候補ツリー、`Aqualumen-entity-light-21.zip`（ラボ導入用。未インストール）
- `probe/entity_probe.cpp` と出力 `probe/probe-output.txt`、`probe/probe-output-timing.txt`

## 証拠（GPU: NVIDIA GeForce RTX 3080 Ti, GL 4.6.0 NVIDIA 580.173.02, EGL）
`probe/entity_probe release/shaders shaders` → 32 PASS / 0 FAIL。候補の実ソースをそのまま使用し、CPU 倍精度の oracle と照合した。
- 全プログラムのコンパイル/リンク: release 26 → 候補 27。`ENTITY_LIGHT_SHADOWS=0` でも 27。shadow_entities の画像ユニットは 5/8。
- 太陽影: depth・shadowcolor0・shadowcolor1 が従来の `shadow` とビット単位で一致（35,874 texel）。除外対象のエンティティも同様に一致。
- フィルタ: ID −1/0/21002 と頂点 α 0.05 は保存 0。
- 正確性: 40,000 線分（軸平行 6,000 本、格子全域 4,000 本を含む）で GPU と、同じ 8×8 格子の CPU 結果の不一致 0。4 m 立方体 + 22 m 斜めシート: 20,000 線分で不一致 0、overflow 0。
- 個別ケース: 間にある遮蔽物は影を落とす / 脇を通る線分・受光点の背後・光源の先は影を落とさない / 他のエンティティは手持ち光を遮る / 自分の体は手持ち光を遮らないが設置光は遮る / 切り抜きの穴は光を通す。
- 時間変化: 歩くモブが 24 フレームで光線を横切り、全フレームが oracle と一致。デスポーン後と 5.7 m のカメラ移動後に残像なし（未消去の record 画像にはゴミを入れて検証）。
- 実 `lampLighting()`: 発光体半径 0.42 で本影、1/3 刻みの半影、照らされた床を確認（3 サンプル）。1 サンプルでは硬い影。
- 既存の `build/glcheck --local-light-probe`（無変更）を、release と候補（GS 非対応のため shadow_entities だけ除いたコピー）に対して実行し、48 行の出力が全行一致した。
- タイミング（GPU ハーネス。Minecraft のフレーム時間ではない。別のゲーム計測と GPU を共有中、約 1 秒の実行のみ）:
  - 64 体（4,608 三角形）の影描画: 0.028 → 0.082 ms（GS 捕捉込み）
  - 100 万本の線分: 空フレーム 0.052 ms / 遠方に 2 体 0.083 ms / 群れを貫く最悪ケース 6.2 ms（包囲球なしは 13.9 ms、同一実行内で交互に計測）
  - この計測は作業量上限 1024 の時点のもの。線分あたりの最大は 214 単位で、どちらの上限にも届いていない。

## 未検証・制約（正直な開示）
- **Iris 上では一切実行していない。** Iris の前処理/パッチ、エンティティ ID の頂点属性化（GS 内では `entityId`→`iris_entityInfo[0].x`。バイトコードで確認）、一括描画、毎フレームの消去、影パスでの memory barrier（shadowcomp 後）は、jar の読解とプローブでの模擬に基づく。
- 生きたモブでの on/off/横断の証拠、実フレーム時間、見た目の確認は Codex のラボ担当。プローブのモブは 6 直方体の人型と板。
- reversed カリングでは shadowDistance(144 m) 内のエンティティが方向に関係なく影パスに入る（バイトコード読解）。ただし画面外のエンティティが実際に捕捉されるかはゲーム内で未確認。
- 切り抜きは 1 辺 8 格子。8×8 テクセルの面は再現誤差 0 だった。一方、1 辺 16 テクセルに 1 テクセルの市松模様という最悪ケースでは 38% が不一致になる。
- 線分の形をしたプリミティブ（leash/lines）は Iris が `shadow` に送るので GS の対象外。ただし MOD が三角形以外の描画を shadow_entities に流すと、その描画は捨てられる。
- 透明化した味方のエンティティ（α 0.15）は影を落とす。アイテム・投射物は意図的に影を落とさない。半透明のスライム外殻は不透明として扱う。
- 容量: 32,768 三角形 / 262,144 ノード / 三角形あたり 4,096 列。超えた分は捨て、meta[2] にフラグを立てる（影が欠ける側に倒れ、残像は出ない）。VRAM 約 9 MB、毎フレームの消去は約 3.5 MB。
- 現実的な混雑シーン（モブトラップ + 多数の松明）では費用がかなり大きくなる可能性がある。上限はあるが、60 FPS は保証できない。

## Codex ラボ確認項目
1. 松明・ランタン・グロウストーンの光源と床の間をゾンビ/クモが横切るとき、影が出て消えること（三人称と一人称の両方）。
2. 手持ち光で自分の影が出ないこと。他のプレイヤーやモブは影を落とすこと。
3. 名札・ビーコン・矢・ドロップアイテム・雷が影を落とさないこと。
4. テレポート・デスポーン・F5 切り替えで残像が出ないこと。`ENTITY_LIGHT_SHADOWS` 0/1 でのフレーム時間。
5. F3 のシェーダーログに shadow_entities の GS コンパイルエラーがないこと。

## README 追記用の参考文献
- T. Möller, B. Trumbore, "Fast, Minimum Storage Ray/Triangle Intersection", JGT 2(1), 1997.
- T. Akenine-Möller, "Fast 3D Triangle-Box Overlap Testing", JGT 6(1), 2001（分離軸）.
- J. Amanatides, A. Woo, "A Fast Voxel Traversal Algorithm for Ray Tracing", Eurographics 1987.
- J. C. Yang, J. Hensley, H. Grün, N. Thibieroz, "Real-Time Concurrent Linked List Construction on the GPU", EGSR 2010.

## 再実行
```
g++ -std=c++17 -O2 build/entity-light-21/probe/entity_probe.cpp -o build/entity-light-21/probe/entity_probe -lepoxy -lEGL
build/entity-light-21/probe/entity_probe release/shaders build/entity-light-21/shaders [--timing]
```
