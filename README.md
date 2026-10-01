# Aqualumen 0.3.0

Minecraft Java版向けのオリジナルIrisシェーダーと水面インタラクションModです。0.3では水の色・反射の細かすぎる筋・夜間の発光感・雲と明部の描写を見直しました。画質優先の実験版で、実写級の完成品や完全な流体シミュレーターではありません。

## このPCで使う

Prism Launcherの **Aqualumen Lab** を起動してください。新版シェーダーと専用Modを有効にしてあります。既存のインスタンス・ワールドは変更していません。検証用の自動カメラ操作は通常利用時には無効です。

- Minecraft 1.21.1 / Java 21 / Fabric Loader 0.19.5
- Iris 1.8.8 / Sodium 0.6.9
- RTX 3080 Ti / 12 GB、OpenGL 4.3以上必須
- Ryzen 9 5900X / RAM 48 GB、専用インスタンスはJava 21 Generational ZGC・ヒープ2〜6 GB
- 測定条件は2560×1440、描画12・シミュレーション6チャンク、標準 `BALANCED`、FPS無制限
- 通常起動は画面に収まる1600×900ウィンドウ・上限120 FPS。F11で画面全体へ切り替えられます。
- ユーザーの方針変更に合わせ、画質を優先します。FPSは観測値として記録し、最低60 FPS保証や合否条件にはしません。

配布物: [シェーダーZIP](dist/Aqualumen-0.3.0.zip) / [専用Mod](dist/aqualumen-physics-0.2.0.jar)。描画側の更新なので専用Modは検証済みの0.2をそのまま使います。別の対応環境では、それぞれ `shaderpacks` と `mods` に入れてIrisから選択します。ZIPだけでも光学・風波は使えますが、接触波紋とディメンション判定にはModが必要です。ModはMinecraft 1.21.1 / Iris 1.8.8のAPIに固定しています。

設定は軽量・標準・高画質です。まず標準を使い、実際の負荷に応じて軽量へ変更してください。

## 水と光

風波は24成分（軽量12・高画質32）の方向性を持つ有限Fourierスペクトルです。重力・表面張力の分散関係、解析的な勾配・曲率、ピクセル幅による帯域制限を使います。未解像の傾斜分散を反射の粗さに移します。FFT海洋シミュレーターではありません。

Fresnel反射・Snell屈折・水中からの全反射・RGB別のBeer–Lambert減衰を実装しています。画面内の深度から屈折光路を反復推定し、浅瀬の初期光路は局所水深と屈折方向から求めます。画面外の反射は環境色へフォールバックします。水中の散乱色を空・太陽・月・ブロック光に結び付け、無照明の水自身は発光しません。RGB値は選んだ澄んだ水の外観であり、実測海水の分光校正ではありません。水底のコースティクスは波面の曲率と有限な光源幅から光束の広がりを推定する、明るさ制限付きの近似です。

岸では推定水深に応じて波を弱め、泡を描きます。画面内の深さ推定であり、実際の砕波・泡粒子・水量移動ではありません。透明ブロックは通常のアルファブレンドで重ねますが、複雑な透明物の完全な順序独立描画は行いません。

空は球状大気のRayleigh/Mie単一散乱を数値積分し、毎フレーム1024×512のLUTに保存します。空の補間は経度の継ぎ目と予約行を明示的に扱います。直接太陽光の大気透過率を予約テクセルへ一度だけ計算し、地形・水・光芒で共有します。地表近くの密なエアロゾルを取りこぼさない積分区間を使います。洞窟の直接光・霞・空の反射は天空光で制限します。

雲は1450〜2200 mの曲面を持つ体積層です。3次元密度、視線32区間、光源方向6区間、Beer–Lambert減衰で厚みと内部の遮光を近似します。風・雨天の雲量を描きますが、熱力学や雲の流体計算ではありません。直接太陽光の雲による減衰はカメラ位置で共有する近似で、ワールド全域の雲影ではありません。多重散乱・大気との結合・地面の環境光・月光は近似、月相は固定満月です。Nether/Endには簡易環境色を使い、地球の太陽・雲を出しません。

影は2048 px・8サンプル、光芒は10ステップが標準です。HDRはRGB共通の柔らかい圧縮で明部の色比と強度の違いを残し、軽い空間フィルターを適用します。夜間は太陽高度に応じた簡易露出補正を使い、夜間倍率を設定できます。これは眼の順応や実写カメラの校正モデルではありません。TAA・完全なGI・ワールド空間のレイトレーシングはありません。

## 実際の波紋計算

Modは水に触れているプレイヤー・ボートなどの位置と移動を読み取り、最大8接触をシェーダーへ送ります。ブロック・エンティティ・サーバーの物理は変更しません。ネットワーク送信やチャットコマンドも行いません。

GPU上の512×512・64 m四方の持続する高さ/速度場を、2パスの画像ping-pongで更新します。波速2.5 m/s、セル0.125 m、フレームdt上限0.05 s・2分割。2次元波動方程式のCFL値は最大0.5で安定域内です。有限半径の接触力で波が伝播し減衰します。ポーズ中は停止し、カメラ移動時は整数セル分を引き継ぎ、大きなテレポート・水位・ワールド変更時にリセットします。

これは **局所的な線形波高シミュレーション** で、Minecraftの水量・流れ・浮力を置き換えるNavier–Stokesソルバーではありません。同じ高さの壁で隔てられた池には完全な接続判定がなく、流れる水・滝・氷・細かな岸の境界条件も近似です。描画側は選択された水位との差0.30 m以内に制限します。処理落ちでは安定性優先で進行時間を制限します。

## 検証とレビュー

```bash
cd /home/kusutohu/repos/aqualumen
make check
python3 tools/build.py
bash tools/build-physics-mod.sh
```

`make check` は実機GPUで11組の描画シェーダーと3本のcompute shaderをコンパイル・リンクし、実出力でFresnel/全反射/吸収、浅瀬の初期光路、非発光の散乱、空LUTの補間・継ぎ目・予約行、HDR明部の区別、大気透過、波紋の初期化・接触応答・最大dt安定性・整数セル移動・減衰・テレポートリセットを検証します。これはMinecraftのFPS測定とは別です。

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

## 実装の参考

- [Irisパイプライン](https://shaders.properties/current/reference/programs/overview/) / [Custom Images](https://shaders.properties/current/reference/buffers/custom_images/)
- [NVIDIA: 波の物理モデル](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)
- [NVIDIA: GPU上の波動方程式](https://developer.nvidia.com/gpugems/gpugems2/part-vi-simulation-and-numerical-algorithms/chapter-44-gpu-framework-solving)
- [NVIDIA: 水底の集光](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)
- [Bruneton: 大気散乱](https://ebruneton.github.io/precomputed_atmospheric_scattering/)

既存シェーダーパックのコード・有料アセットは使用していません。自作部分はMITライセンスです。
