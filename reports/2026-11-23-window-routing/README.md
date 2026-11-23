# 松明が板ガラスを照らすときの描画

RTX 3080 Ti、Minecraft 1.21.1、Iris 1.8.8、Sodium 0.6.9で、近くの松明から色ガラスを通る光を描いた。通常の照明と、ガラスの外形を利用する照明を別々の描画プログラムにした。窓の近くに松明があって、保存した光路に実際に窓が含まれる場合だけ後者を選ぶ。色、遮蔽、24点の光源サンプルは以前の窓版と共通。[配布用ZIP](../../dist/Aqualumen-Window-Routing.zip)・[部屋と白樺林のゲーム画面](room-and-birch.jpg)

## 通常描画の実測

2560×1440、12チャンク。表はGPUタイムスタンプを切って取得したMinecraftの平均フレーム間隔。元版は Sunlit-Panes、従来の試作は Window-Cells。前回の両版の結果を再利用し、今回のZIPで同じカメラとブロックを再現した。部屋は赤窓から板なしへ戻る順の比較。林は松明0本から4本へ増やした。

| 場面 | 元版 | 従来の試作 | 今回 |
| --- | ---: | ---: | ---: |
| 板なしの部屋 | 26.49 ms | 32.69 ms | 26.37 ms |
| 松明と赤窓 | 62.90 ms | 47.84 ms | 47.62 ms |
| 白樺林、松明0本 | 40.00 ms | 40.80 ms | 39.76 ms |
| 白樺林、松明4本 | 83.82 ms | 109.73 ms | 83.74 ms |

今回の部屋は板なし380フレーム、赤窓210フレームを集計。赤窓の差は平均約15.27 ms。林で元版との小さな差に再現性があるかは、この回数からは判定できない。距離を離した板と松明の場面は26.60 ms、板のそばの松明を消した場面は19.87 msだった。[部屋の計測](selective-room/summary.json)・[林の計測](selective-birch/summary.json)・[元版の部屋](../2026-11-23-pane-beam/control-reverse/summary.json)・[元版の林](../2026-11-23-pane-beam/birch-control/summary.json)

## 光と切り替えの検査

- 板なし、赤、二色、石の縁、牛、視点を少し移動した赤窓、板の撤去後の7場面で、壁の同じワールド座標102,285組の透過RGBを元版と照合した。8ビット各チャンネルで差は0だった。赤窓の場面では、実際に外形を使って計算した11,050点に着色があった。[場面別の照合](selective-optics/transmission.json)
- Fableの提案を受け、通常のパックとは別に、両方の描画プログラムからフレーム番号と経路を5個の描画先に刻んだ。7場面の連続5,120フレームで、画面内9点の全出力が当該フレームと一致した。通常の経路3,318フレーム、窓用1,802フレーム、途中の切り替え4回。松明を消した場面と板を約26 m離した場面では、ボクセル場に板が入っていても通常の経路を選んだ。[フレームごとの照合を集計した記録](selective-freshness/freshness.json)・[Fableの助言](advisor.txt)
- カメラ周辺の全512タイルのうち、光源一覧が空になったタイルの印を消す。更新されたタイルでは、同じ光源スロットの二つのビットが同時に立っている受光セルを探す。各タイルでは有無のみ保存し、GPUが最後に一つの選択値に集約する。二つの頂点プログラムは同じ値を読む。最初の描画後のバッファ交換を五つとも無効にし、二番目の描画の後に一度だけ交換する。[Irisのバッファ交換仕様](https://shaders.properties/current/reference/shadersproperties/rendering/#flip)・[Irisの描画順序](https://shaders.properties/current/reference/programs/overview/)
- 最初の試作はワールドに板があるだけで経路を切り替えた。板なし26.70 ms、赤窓47.71 ms、白樺4本83.94 ms。初回にIrisが計算グループ数の1引数表記を拒否し、別の検査用パックでは17枚目の画像をIrisが拒否した。どちらも検査結果から除外した。配布版のグループ数は3引数表記、検査用の印は既存画像の未使用領域に保存した。[起動失敗](route-room/complete.json)・[検査用パックの失敗](route-freshness/complete.json)

専用の照明プログラムは、カメラの近くに対象の光路があれば画面全体で動く。視界の外に点灯した窓がある林は、通常の白樺4本とは別の条件として扱う。色ガラスの見え方について、今回の比較対象はMinecraftの元のAqualumen版である。

## 雪の村でのサバイバル

以前の「赤窓と玄関の松明」のセーブから開始し、ポピーを採った雪原まで歩いた。地面に通常のランタンを一つ置き、同じ家に帰った。ゲーム内の歩行統計は147.87 m。新しいセーブでランタンが4個から3個に減り、設置位置、赤窓、玄関の松明、屋内の魂の松明が保存されていることを確認した。チートなし、サバイバル、自然な時刻・天候の進行を維持。今回の追加は8,292ティック。3シードで重複を除いた累計は124,823ティック、5.201マイクラ日、1,325.48 m。[雪原に置いたランタン](../2026-11-22-ceiling-return/village/snowfield-trail-lantern/snow-trail-lantern-ingame.png)・[村へ戻った画面](../2026-11-22-ceiling-return/village/snowfield-trail-lantern/home-after-the-snowfield-ingame.png)・[引き続き遊べるセーブ](../../dist/Aqualumen-Snowfield-Lantern.zip)・[セーブ内容](../2026-11-22-ceiling-return/village/snowfield-trail-lantern/save.json)・[累計](playtime.json)

このZIPの40プログラムはNVIDIAドライバとMesa llvmpipeでコンパイル・リンクした。隔離した実MinecraftでAqualumen Lighting Compiler 0.3.0を使用した。通常Labは1.8.0を選択、physics 0.2.0を使用している。[ビルド照合](build.json)・[RTX](compile-nvidia.txt)・[Mesa](compile-mesa.txt)・[照明コンパイラ](../../dist/aqualumen-lighting-compiler-0.3.0.jar)
