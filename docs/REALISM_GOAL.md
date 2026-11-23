# Water and sunlight realism goal

## 長期目標　森から地下を抜け、雨上がりの水辺に戻る

2026年11月24日時点で、3シードのサバイバルを計144,009ティック（約6.00ゲーム日）、1,499.86 mまで記録した。色付き板ガラスを通る視線には厚みに応じた吸収を適用し、赤板を重ねた条件や水槽の水底まで届く光をRTX 3080 Tiで確認した。夜の屋外では、同じ位置と時刻で松明の本数と降雪を変え、フレーム時間の増加を調べる。[実プレイの集計](../reports/2026-11-23-camera-glass/playtime.json)・[色付き板ガラスの実機検証](../reports/2026-11-23-camera-glass/README.md)

**長期ゴールは、性格の違う3シード以上で計100ゲーム日のサバイバルを遊び、建て替えた拠点に何度戻っても、個々の光源・遮蔽物・反射を見て説明できる状態にすること。** 例えば、窓から夕日が入る木の家で松明を二本置き、一方を石で隠し、もう一方を持って地下へ下りる。留守の間に雨が降り、帰ると天窓の月光、屋根の下のランタン、色壁からの反射がそれぞれの場所に見える。この変化を同じセーブで、設置・撤去・昼夜・再起動をまたいで追う。

100日は実際に建築・移動・採掘・帰還したセーブの経過をシードごとに記録する。天候や時刻を固定する実験は光学の確認に使う。途中で同じセーブから試し直した区間は重ねて日数に足さない。最初の30日で森・村・洞窟をつなぎ、その先は多光源の拠点、移動する動物、小さな穴や色ガラスを通る反射、暗順応、別次元からの帰還を扱う。100日後も残る破綻は、その場所のセーブと操作を次の修正に使う。

赤い窓をはめた雪村の家を開き直し、暖色の松明を玄関の外壁に掛けた。室内の魂の松明、作業台、窓、玄関ランタンをセーブで確認した。3シードで累計4.85546ゲーム日、1,177.61 m。[雪村の朝の実画面](../reports/2026-11-23-pane-beam/village.jpg)・[続きから遊べるセーブ](../dist/Aqualumen-Lit-Red-Window.zip)・[経過の内訳](../reports/2026-11-23-pane-beam/playtime.json)

雪村でポピーを摘んで家まで持ち帰り、作業台で赤い染料と板ガラスを作って玄関脇の窓にはめた。3シードを合わせて4.7495ゲーム日、1,166.07 m。松明の光は、つながった板の厚みと通る向きに従って色が変わる。白壁では赤板と青板の差を、ガラスを直接見ていない10,421地点で確認した。[村の窓と所持品](../reports/2026-11-23-stained-panes/window.json)・[白壁の比較](../reports/2026-11-23-stained-panes/README.md)

夕方の白い床では、赤い板ガラスを青い板に替えても直射日光が変わらない問題を確認した。日光の光路にも板の厚みを反映すると、板越しの3,173地点で、通常画面の赤板−青板の差が中央値 (+16, −22, −38) 階調になった。石を置くと同じ3,173地点すべてで直射成分がゼロになった。[同じカメラで撮った床](../reports/2026-11-23-stained-panes/sunlight.jpg)・[直射成分の測定値](../reports/2026-11-23-stained-panes/sun-filtered-direct.json)

白樺の東側の松明を回収して北西に移し、東側の樹皮に幹自身の影が残るところまで同じサバイバルを進めた。3シード累計は4.34154ゲーム日、1,019.52 m。設置松明の可視率をワールド座標で再利用する試作は、木陰と動物の比較で元の画を保ったが、白樺4灯・1440pの平均フレーム間隔は両版とも約83 msだった。[設置前後の実画面](../reports/2026-11-23-torch-cell-shadow/birch.jpg)・[検証記録](../reports/2026-11-23-torch-cell-shadow/README.md)

松明から光が通りうる区画に探索を絞り、白樺林4灯の1440pで平均フレーム間隔が105.14 msから83.19 msになった。森の5視点と幹・牛の10場面で旧版と一致する地形の可視率を確認した。サバイバルでは白樺から岩陰の野営地まで上り、入口に松明を置いて戻れるセーブを作った。3シードのワールド時計は累計3.969日、移動は980.48 m。[走査、照明とプレイの記録](../reports/2026-11-23-torch-brick-scan/README.md)

白樺林でカメラをブロック境界の両側へ2 cmずつ動かし、実際の地形に届く松明の光を測った。松明4本の輪郭補正版では、地形の照明パスが31.54 msから22.95 msに短縮した。地面で火の可視率が66.7%から0%へ飛んだ場所は、24本の版で45.9%から37.6%に変わり、独立参照の39.4%から36.0%に近づいた。一方、24本版の平均フレーム間隔は215.68 msで、昼のその画素の表示RGBは輪郭補正版と同じだった。[五つの視点での検証](../reports/2026-11-23-torch-shadow-integral/README.md)・[計測した草地](../reports/2026-11-23-torch-shadow-integral/grass-display.png)

サバイバルでは同じ白樺の反対側に魂の松明を設置し、幹を回って暖色と青色の光を確認した。再保存した地形で二本の松明と白樺を確認している。3シード合計のワールド経過は3.85217ゲーム日、歩行は962.75 m。今回増えた5,376ティックには入場後のシェーダー準備時間も含む。今回の操作区間は61.9秒だった。[森での画面](../reports/2026-11-23-torch-shadow-integral/survival.jpg)・[経過と操作時間](../reports/2026-11-23-torch-shadow-integral/playtime.json)

設置灯から見た火の範囲全体に触れるブロックを探し、幹の奥や斜めに段差が続く地面の半影を描いた。白樺林5地点の同じ地表で、2 cm移動したときの可視率の変化が参照から10ポイント以上ずれた箇所は、三者で照合できた同一ブロック内の24,856組で617から0になった。4灯・1440pでの配布版の平均105.97 msは軽い輪郭補正版の69.01 msより長く、24点を広い範囲で使う版の215.68 msより短い。通常設定での長距離歩行、透過した葉が何枚も重なる場所は今後の対象。[実装と実測](../reports/2026-11-23-torch-shadow-integral/README.md#配布用の地形版)・[配布用地形版](../dist/Aqualumen-Torch-Shadow-Geometry.zip)

白樺の脇に土を置いた。設置松明から壁を照らすと、幹と土の間から見える火の面積に応じて影が重なる。4灯の白樺林で測った25,727件の半影では、独立参照との平均誤差が5.78から2.53ポイントに下がった。試験場では牛が影を落とした5,261地点で通過後に元の可視率へ戻った。自然に昼夜が進む継続セーブは3シード・3.62817日、957.60 m。残る課題は、4灯時の描画負荷と、葉が火を部分的に隠すときの透過を検証できる参照の整備。[幹と土の実画面と測定](../reports/2026-11-23-mixed-occluders/README.md)・[サバイバルの白樺](../reports/2026-11-23-mixed-occluders/survival.jpg)

設置した松明と白樺の間を通る光線を調べ、白壁の半影の縁に残っていた段を減らした。自然の白樺林4灯では、参照計算に対応づけられた25,727件の半影で可視率の平均絶対誤差が11.35ポイントから5.78ポイントに下がった。牛の通過時には実際に火を隠す部分を調べ、光路から外れた側の壁1,513地点すべてで幹の影を保てた。サバイバルでは石の野営地から白樺まで歩いて松明を置き、3シード合計3.5658日、950.08 mに到達した。[実機の半影検証](../reports/2026-11-23-placed-penumbra/README.md)・[牛と幹の実画面](../reports/2026-11-23-placed-penumbra/animal-movement.jpg)・[白樺での設置と回り込み](../reports/2026-11-23-placed-penumbra/survival-birch.jpg)・[継続台帳](../reports/2026-11-23-placed-penumbra/playtime.json)

最初の三昼夜で村の窓や軒を造り替え、森に置いた火を残してチャンクの外まで遠征する。30日までに地下の溶岩をせき止め、ネザーから拠点へ帰る。増減した溶岩面、色ガラス、葉、動物、開閉する扉が、それぞれに届く光と影を変える。雪から雨へ歩いた後も、同じ屋根の下に置いた灯りと、外で濡れた石の見え方を追う。

完成の基準は、初めて訪れる普通のサバイバルワールドでも、プレイヤーが光と遮蔽物を動かした結果を自分の目で追えること。松明を二本に増やす、一本を持って歩く、片方だけを石で遮る、赤い床を白い石に張り替える、窓を開けて雨の夜を迎える。この順序を変えても、照らされる面・反射色・影がそれぞれの操作に応じて変わるところを目指す。さらに動物が火の前を通る際の影、壁から天井へ二度返る光、洞口から外へ出たときの眼の順応まで、同じ家と隣の自然林でつなげる。

光漏れや光源の消失を見つけた場所は、同じセーブと操作で再現して修正する。RTX 3080 Tiのフレーム時間、初回起動、初めて地形を読み込むときの引っかかりも記録する。各段階で遊べる版を出し、次の四つを普通のプレイで確かめる。

1. **木陰に差す光**　木を一本残して周囲を伐ったとき、片側に屋根を増築したとき、同じ幹のどの面に空が見えるかが変わる。プレビュー4で地形の方向別天空光を導入した。次は日なたの草や石が幹に返す光を扱い、地面だけを日陰にした状態・色の違う床・曇天を比較する。[プレビュー4の白樺](../reports/2026-11-21-canopy-sky/daylight/birch.jpg) · [地面からの反射の推定](../reports/2026-11-21-canopy-sky/ground-reference.json)
2. **動く物にも届く光**　松明と青いランタンの間を動物が通る。毛や足元が受ける天空光、体が片方の光源に落とす影、濡れた床に映る光を一つの動画で確認する。ランタンを手に取って歩く往路と、床に戻した復路を残す。
3. **建て替えた家で一日を過ごす**　日中に窓を塞いで別の壁に開け、夜は室内だけを照らし、翌朝は雨の屋外へ出る。明暗への順応、扉を通じた光、窓の外の雨、濡れていく面と軒下の乾いた面を、時間が進む同じセーブで追う。
4. **遠征と帰還**　密林・開けた村・標高差のある地形で地下や別次元まで移動し、拠点を再読込する。灯りの再出現、格子境界で動く影、遠景の切り替わり、初回コンパイルとフレーム時間を長い移動で確かめる。別シードで見つかった破綻は、そのセーブと再現操作を開発に戻す。

拠点の木陰には、同じ幹を別方向から照らす松明と魂の松明を一本ずつ置く。片方を石で遮り、もう片方を手に取って木の裏へ歩き、日没後にも同じ道を戻る。幹や地面に残る暖色・青色、葉を通る日射、足元の接触影を固定カメラと一人称の往復動画で確かめる。次に地下で溶岩を水で固め、地上の灯りを残したままネザーを往復し、再読込した拠点を比較する。この一連の操作を、林冠の密度や地形の異なるシードへ持ち込む。[木陰の実画面](../reports/2026-11-21-leaf-light/timing-cone-daylight.jpg) · [別光源を加えたときの洞窟照明](../reports/2026-11-21-lava-light/README.md)

プレビュー7では、ランタンの光が赤い壁ともう一枚の壁を経て天井に届く。三点の反射を記録し、光源・壁材・仕切りを変えて確認した。雪の村には平原から151.28 m歩いて戻り、もとのランタンの下に魂の松明を置いた。翌日には裏窓を板で塞ぎ、玄関脇に新しい窓を開けた。家を開き直すと、前庭から窓越しに内装が見える。次は雨の朝の往復で、軒の下に入る日光、室内灯が作る影、目の順応を別々に追う。二灯の夜に落ちたフレームレートについては、二回反射の計算を減らせるか、灯りの移動・撤去で残像が出ないかもあわせて調べる。[二度返る灯りと実測](../reports/2026-11-22-ceiling-return/README.md) · [改築の実画面](../reports/2026-11-22-ceiling-return/village/windows.jpg) · [村の改築後のセーブ](../dist/Aqualumen-Window-House.zip) · [オーク林の遠征セーブ](../dist/Aqualumen-Woodland-Expedition.zip)

プレビュー8では、森の洞窟で昼の入口を見上げたときの露出倍率がプレビュー7の16.0倍から12.4倍に下がり、岩壁に向き直ると15.9倍に戻った。別にRTX 3080 Ti（2560×1440、12チャンク）で夜の二灯と昼の屋外を各2組測ると、プレビュー7に対するフレーム時間の増加は平均で最大1.96%、p99で最大6.66%だった。次は雨の朝、改築した同じ家の軒下と室内を往復し、軒下に差す日光、室内灯が落とす影、目の順応を個別に追う。[洞窟での露出の比較](../reports/2026-11-22-eye-adaptation/README.md) · [二場面のフレーム時間](../reports/2026-11-22-eye-adaptation/frame-times.json)

オークの夜道では、設置した松明を外して戻すと幹の脇の草地が明るくなり、根元を斧で切ると幹の裏にも光が届いた。幹の裏703点で測った点灯時と消灯時の画面輝度差の中央値は伐採前−4.15、伐採後+26.33だった。切った木でランタンの道しるべを建て、継続区間は3シード・2.13ゲーム日になった。[6枚の比較とセーブ](../reports/2026-11-23-oak-shadow/README.md)

オークの幹を残し、同じ時刻・視点・露出で葉の反射を切り替えた。暖色の松明で幹の裏の草703地点が中央値3.07階調、魂の松明で2.15階調明るくなった。通常のサバイバルではランタン柱から湖畔へ47.11 m進み、砂を掘ったくぼみへ水を引き、暖色と青のランタンで二地点を結んだ。3シードでの累計は2.2545ゲーム日、539.97 m。雨の真夜中の隔離走行では、樹冠の下まで暖色・魂・手ぶらで歩いた。草130地点を追うと、照明格子の境界をまたぐ約0.22 mで輝度が暖色で5.96、手ぶらで10.92階調上がった。同じ草130地点を同一フレームで露出固定と通常表示に分けて再測定し、約5 cmの境界またぎでは固定露出の往路0.28、復路1.18階調だった。[森の同条件比較](../reports/2026-11-23-leaf-tiles/README.md) · [湖畔のセーブ](../dist/Aqualumen-Lakeside-Lanterns.zip) · [継続日数](../reports/2026-11-23-leaf-tiles/playtime.json)

通常のプレビュー11では湖畔から牧草地まで126.52 m歩き、道に二つのランタンを加え、牛を4地点で観察した。木陰に置いた魂のランタンは草を青緑に照らし、隣の幹の影も読み取れる。3シードの累計は2.6205ゲーム日、666.49 m。[森での画面と雨夜の往復](../reports/2026-11-23-wet-oak-motion/README.md) · [牧草地のセーブ](../dist/Aqualumen-Meadow-Trail.zip)

雨夜の草130地点では、プレイヤーの体が設置灯を遮る影だけを取り除くと、手ぶらで約1.2〜1.3 m歩いたときの局所光の変化が往復とも93〜95%小さくなった。松明を持った同じ道では減少は6〜7%だった。木陰を照らす光と、その前を横切るプレイヤーの影を区別できた。[同一フレームでの比較](../reports/2026-11-23-wet-oak-motion/README.md#草に落ちたプレイヤーの影)

幹が光源面の全体を隠す場合に影計算を省く試作を、松明4本の白樺林で測った。プレビュー11との比較でGPU平均は69.01→67.06 ms、順序を逆にしGPU計測を外した平均フレーム間隔は74.46→72.40 ms。樹皮の差は最大1階調だった。プレビュー12を配布し、実ゲームで手持ち灯を柱の左右に動かしたときの影と、牛が二色の灯りの間を4.44 m歩いたときの影も確認した。幹の縁の半影には3点サンプルに由来する段が残る。[遮蔽条件・画素・実ゲーム時間](../reports/2026-11-23-torch-umbra/README.md)

牧草地の丘に土の避難所を掘り、奥に魂のランタン、入口に暖色のランタンを置いた。再起動後に別の出口を掘り、以前置いた三灯をたどって湖に戻った。往路40.42 m、復路103.80 m。3シードの累計は3.0615ゲーム日、810.71 mに達した。[丘の避難所](../reports/2026-11-23-torch-umbra/meadow-shelter.jpg)・[夜道と湖畔](../reports/2026-11-23-torch-umbra/lake-homecoming.jpg)・[セーブから集計した経過](../reports/2026-11-23-torch-umbra/playtime.json)

手持ちの松明を持って柱の左右に立ったとき、壁の半影が段になっていた。円盤形の火のうち実際に見える面積を使う実験版では、左の縁で1 cmごとの最大の輝度差が10.77から1.28階調に減った。牛と柱の両方が同じ火を部分的に隠す513地点でも、可視率の平均誤差が0.0630から0.0227に下がった。白樺林の設置松明4本では手ぶらでもプレビュー12より7.18 ms遅く、複数の設置灯の半影を同じ精度で描く費用が残る。通常サバイバルは、森の避難所から持ち帰った土で湖畔に壁を建て、両側に暖色・青の灯りを置くところまで進んだ。3シード・累計3.154375ゲーム日、824.17 m。[壁の実画面](../reports/2026-11-23-torch-penumbra/joint-wall-comparison.png)・[白樺の計測](../reports/2026-11-23-torch-penumbra/forest.json)・[湖畔の朝](../reports/2026-11-23-torch-penumbra/bank.jpg)・[継続記録](../reports/2026-11-23-torch-penumbra/playtime.json)

設置松明4本の白樺林では、滑らかな半影を残しつつ、画面で見える地形の光を最終深度から計算する実験版で、1440pの平均フレーム間隔が79.73 msから66.76 msに縮んだ。湖畔の松明の支えを掘る場面では、78画面で地形への二重加算・加算漏れを検出しなかった。雨夜の丸石では線形RGB差が最大0.031まで残る。通常プレイは湖畔の松明を一段低くするところまで進み、3シード合計で3.20379ゲーム日、833.54 m。[検証と計測条件](../reports/2026-11-23-visible-terrain/README.md)・[湖畔の画面](../reports/2026-11-23-visible-terrain/lowered-torch.jpg)

プレビュー13で湖畔から天然の岩陰まで89.89 m歩き、以前置いた二灯を湖畔に残して、岩棚に魂のランタンを設置した。昼夜と天候が自然に進む3シードの累計は82,109ティック（3.42121ゲーム日）、923.43 m。雨の真夜中に同じ岩陰へ入る4秒間も別の複製で収録した。濡れた丸石の照明を同じ露出で比較すると、不透明面における表示値の最大差は1階調だった。白樺林・松明4本・1440pで、配布用ZIPの平均フレーム間隔は66.33 ms。[通常プレイの画面](../reports/2026-11-23-wet-receiver/survival-walk.jpg)・[雨の入口の動画](../reports/2026-11-23-wet-receiver/under-stone-rain.mp4)・[継続セーブの集計](../reports/2026-11-23-wet-receiver/playtime.json)

その岩棚に戻り、木のつるはしで石を掘り、魂のランタンの隣に暖色の松明を掛けた。3シードの通常サバイバルは累計83,233ティック（3.46804ゲーム日）、929.48 m。隔離した木陰では、設置光源の全透過判定をVRAMに残す試作を、幹の撤去と牛が横切る途中にも元の光線計算と比較した。[岩棚の画面](../reports/2026-11-23-torch-open-volume/stone-niche.jpg)・[プレイの内訳](../reports/2026-11-23-torch-open-volume/playtime.json)・[キャッシュの検証](../reports/2026-11-23-torch-open-volume/README.md)

濡れた丸石の映り込みでは、Irisから受け取った水平面の向きが約0.45度傾いていた。水膜の実験版では、床の三角形と頂点法線を照合してから反射に使う向きを戻す。通常のプレビュー13と補正版の両方で、同じ松明4本の白樺を1440pで計測し、暗い樹皮と遠い草の画素も比較した。[反射が変化した位置](../reports/2026-11-23-wet-receiver/flat-stone.jpg)・[試作の実装と照合](../reports/2026-11-23-wet-receiver/README.md)

プレビュー10では二回反射の96本のレイを保ち、白樺の木陰に松明4本を置いたときのGPUフレーム時間を2回の比較で4.07 ms、4.62 ms短縮した。通常プレイでは森の幹の裏の魂の松明を回収・再設置し、別シードの洞窟で石を掘って二色の灯りを残した。継続区間の累計は3シード・1.94ゲーム日。暖色の松明を至近距離で持つとオークの木目が弱まるため、画面に変換する前後の樹皮を同じ位置で測定している。[計測とセーブ](../reports/2026-11-23-torch-density/README.md) · [継続区間](../reports/2026-11-23-torch-density/playtime.json)

同じサバイバルの森では、前回の時刻41023から59304まで通常の昼夜を進め、以前置いた松明を残して167.78 m歩いた。晴れた木陰で普通の松明を手に持つと、幹の赤成分が49から132に上がり、しまうと49に戻る。野生の牛を近くで安定して見られる牧場を食料と一緒に整えることも、この先の拠点づくりに含める。[手持ちの灯りを替えたオーク](../reports/2026-11-21-animal-light/woodland/torchlight.jpg) · [旅の保存記録](../reports/2026-11-21-animal-light/woodland/checkpoint.json)

プレビュー6では、牛が二つの灯りの間を自力で4.44 m歩き、暗くなる壁と残る光の色が入れ替わるところを記録した。日中には本物の牛の毛へ地面の色が届き、屋根を掛けると色差が消える。次の室内ではランタンの直射が届かない天井を選び、赤い壁、その向こうの白い壁を順に経由する光を、プレイヤーが壁を建て替えた前後で追う。三か所のどこを塞いでも二回反射だけが消える配置を数値積分した。[二灯の動画と実測](../reports/2026-11-21-animal-light/README.md) · [二回反射の光路と基準値](../reports/2026-11-22-ceiling-return/README.md)

プレビュー5では、夕方の白樺に普通の松明と魂の松明を同時に置き、普通の松明側だけを石で遮った。片方を外す対照を含む七条件で、木陰に独立して落ちる暖色と青色を確認した。正午には地面の反射を追加し、現地の床材30個を赤から白に替えたときの反射光をゲームから直接読み出した。石屋根を載せると、日射が床で反射して幹に届く成分の色差は消えた。次の通し試験ではこの二本の間を動物が通る場面と、室内で色のある面を二度経由する経路を扱う。[二本の実画面](../reports/2026-11-21-ground-return/lights/two-lamps.jpg) · [床が返す光の検証](../reports/2026-11-21-ground-return/README.md)

同じオーク林のセーブをプレビュー5で二回続けて遊び、雨の中をさらに64.99 m歩いた。木陰に残した一本は、再起動と水辺への往復を経ても同じ座標に保存されている。暖色の松明の届く範囲を出ると、持ち歩いている魂の松明をしまったときに足元が暗くなる。次の遠征を始めるセーブ時刻は 41023 ティック。[連続プレイの抜粋](../reports/2026-11-21-ground-return/walk/walk.mp4) · [三つのセーブの照合](../reports/2026-11-21-ground-return/walk/checkpoint.json)

プレビュー4のオーク林では、松明を地面に立てて手をシャベルに戻し、土一個で光路を塞いでから開け直した。葉の暖色は土を壊すと同じ位置に戻った。同じセーブからの別のプレイでは、二つの照明格子の境界を徒歩で往復し、水辺から戻って保存した。二つのプレイは同じ保存地点から分岐するため、長期試験の経過日数には重ねて加算しない。[松明・土壁・魂の松明を比較](../reports/2026-11-21-canopy-sky/shaded-oak/oak.jpg) · [歩行・建築の記録](../reports/2026-11-21-canopy-sky/woodland/p4-play/complete.json)

1.9.0プレビュー3では、天然洞窟の岩棚に魂の松明を置き、溶岩25マスを黒曜石に変えた。岩の青は残り、溶岩が残る奥だけが橙色になった。暗がりで凝灰岩を掘るとひびが見え、手を離すとその部分に元の色が戻った。この地点のセーブを保存し、次の往復も同じ世界と時刻の続きで検証できるようにした。[洞窟の実画面](../reports/2026-11-21-lava-light/cavern/ordered-survival/cavern-light.jpg) · [採掘中・中断後の比較](../reports/2026-11-21-lava-light/cavern/ordered-survival/mining.jpg) · [サバイバルの保存地点](../reports/2026-11-21-lava-light/cavern/ordered-survival/checkpoint.json)

この洞窟を実際に保存・終了して開き直し、同じ松明を回収・再設置した。溶岩の残った奥は橙色を保ち、松明を置いた側だけ再び青くなった。通常の一日の24,000ティックのうち、この遠征で連続して進んだのは3,490ティック。今後の移動や建築も、このように同じセーブの経過を記録する。[保存後の消灯と再点灯](../reports/2026-11-21-lava-light/cavern/ordered-return/reopened.jpg) · [時刻とブロック差分](../reports/2026-11-21-lava-light/cavern/ordered-return/complete.json)

同じ白樺をPhoton v1.1とプレビュー3で撮ると、消灯した幹はPhotonでは青みが強く暗い一方、Aqualumenでは中立に近い明るい灰色に見える。次に詰めるのは、樹冠の内側で空のどの方向が本当に見えるか。保存地形とMinecraftの葉テクスチャから20ブロック以内を調べ、受光面への寄与で重み付けすると、遮られない上空の割合は幹の中央で40.4%、松明を置いた草で35.7%、根元で17.6%だった。細い草を立方体扱いした近似なので、これは明るさの設定値には使わない。ほかの森、曇天、日没にも同じ天空光の計算を適用し、松明自身の暖色・青色を保ちながら木陰の奥行きを比較する。[PhotonとAqualumenの実画像](../reports/2026-11-21-lava-light/wall-v190/birch-release-comparison/photon-and-aqualumen.jpg) · [同じ受光点の天空可視率](../reports/2026-11-21-lava-light/wall-v190/birch-release-comparison/sky-visibility.json)

安定版1.8.0では、夜の検証用拠点に暖色と青の松明を残し、徒歩でネザーポータルを往復した。帰還後に同じ白壁を撮ると、それぞれの色が同じ側に残り、保存したワールドでも両方の松明を確認できた。この往復は固定時刻の専用ワールドで行った。プレビュー3で続けている天然洞窟の経過日数は別に数える。[往復前後の実画面](../reports/2026-11-21-portal-return/comparison.jpg) · [次元・座標・保存の記録](../reports/2026-11-21-portal-return/run2/complete.json)

通常のサバイバルで、午後に森へ入り、木陰に松明を置き、片手にランタンを持って洞窟へ下り、動物のいる家を通って夜の川へ出る。一連の操作で光源の位置、物体の形、材質、天候を目で読み取れるところまで作る。逆方向に歩いて、松明を回収し、扉を閉め、雨が上がった後にも同じ光の関係が成り立つことを確かめる。

| 遊ぶ人の操作 | 確かめること |
| --- | --- |
| 木の陰に松明を置く、持ち替える、しまう | 炎を向いた幹や草は暖まり、石で松明の光路を遮るとその暖色が消える。樹冠は太陽を遮り続ける。 |
| 動物がランタンの前を通る | 胴と脚が横切るにつれて壁の影が移り、その場を離れると壁に元の光が戻る。光源の後ろや壁の向こうにいる動物も比較する。 |
| 明るい壁の色を変え、角を曲がる | 赤い壁を照らすと直射の届かない明るい石に弱い赤が返る。白壁、消灯、二つの面の間に仕切りを置いた条件と比較する。 |
| 昼の屋外から洞窟に入り、夕方に出る | 日光から遮られた奥は地上の時刻に左右されず、入口からの距離と向きに応じて空の光が変わる。往復の動画で露出の追従を見る。 |
| 雨の夜、川べりを歩く | 地面や水に映るランタンが視点・波・面の粗さに追従する。光源を回収する、水際から一歩下がる、遮蔽物を置く操作まで撮る。 |
| 同じ道を普通に遊ぶ | 森・建物・洞窟・水辺を昼、夕、夜に通しで遊び、カメラを回しても光が飛ばず、影や反射に残像が出ないことを実映像で確認する。RTX 3080 Ti・1440p・12チャンクの区間別フレーム時間も残す。 |

長期の完了条件には次の場面も含める。松明を置いた地点の一枚だけでは、これらの条件を満たしたとは判定できない。

- **夕暮れの家。** 低い西日が窓から入り、ランタンが暖色、魂の松明が青色を落とす。扉の開閉や歩く動物が遮った光だけが変わり、別方向の灯りとその影はそれぞれ残る。壁・床・動く物体を同時に観察する。
- **洞窟への往復。** 入口から遠ざかるにつれて空が見える方向が狭まり、岩壁への昼光と目の暗順応が別々に変化する。途中で松明を収納し、出口へ振り返っても開口の輪郭が発光したり旧位置の暖色が残ったりしないことを動画で確かめる。
- **同じ岸の乾燥、雨、雨上がり。** 同じ材質・光源配置で、乾いた石、雨に濡れた石、波のある水面を比べる。材質と見る角度によってハイライトの幅や強さが変わり、屋根の下では雨に濡れた効果が弱まる。ランタンを撤去した後の画面を比較する。
- **長時間の通常プレイ。** 自分で置いた灯りを持ち替え、視界外に回してから戻り、チャンク境界を往復する。日が沈み、雨が降り、地下を通り抜ける間、同じ地点で光が突然入れ替わる箇所を探す。区間別のフレーム時間、映像、試せる通常版を揃えてから判断する。

暗いオークの幹から自然洞窟を通り、水際へ戻る最初の徒歩区間を既存の専用ワールドで選んだ。木から洞窟奥まで38歩、そこから水際まで12歩で、足場と頭上2ブロックの空間を保存済みの地形から照合できる。建物内を動く生き物、降雨から雨上がりまでの材質変化、同じ道を反対向きに進む時間帯別の確認も続ける。[実地形の座標列](../reports/2026-11-21-continuous-walk/forest-to-bank.json) · [徒歩経路の抽出](../reports/2026-11-21-continuous-walk/scout.py)

同じ経路を1.5.0の実ゲームで歩き、夕暮れは松明を手に41.2秒、雨の夜はランタンを手に29.3秒の動画を取得した。最初の位置指定の後は足で移動し、どちらも洞窟で振り返り、川岸の同じブロックに立った。夕暮れの二部屋の家でも、扉の向こうの吊りランタン、手前の魂のランタン、西窓から入る日光を同じ画面で追う。[森・洞窟・川岸の動画と記録](../reports/2026-11-21-continuous-walk/README.md)

扉を閉めたときは板と隙間を区別する。1.6.0の通常描画では、同じ白壁にオークの四つの窓、アカシアの縦格子、ダークオークの遮光を確認した。細い窓を使い、影の縁の明るさを独立した面光源計算とも照合した。[扉の実ゲーム比較](../reports/2026-11-21-door-light/window/shipped-projection.jpg) · [半影の照合値](../reports/2026-11-21-door-light/window/shipped-edge-profile.json)

森から夕暮れの家までの短い区間は、独立したクリエイティブワールドでも試せる。並木道から玄関まで歩き、松明を回収・再設置し、二室の間の扉を操作できる。夕暮れを固定して同じ光を見比べるための場所で、昼夜と雨をまたぐ長距離のサバイバル往復は引き続き別に検証する。[遊べる家](../dist/Aqualumen-Lantern-House.zip) · [配布ワールドを歩いた記録](../reports/2026-11-21-door-light/playable/smoke/smoke.json)

保存済みの家では、奥の暖色が扉の開閉で白床に現れたり消えたりする間、手前の魂のランタンは本棚脇の石を照らし続けた。建築直後の同じセッションでは無関係な石の頂点天空光が変わったことがあり、長時間の経路には、既存の家へ戻る場面と、その場で屋根を架けて照明を変える場面の両方を含める。[配布版の室内比較](../reports/2026-11-21-door-light/sky-control/ordinary-house.jpg) · [建築時と再読込後の天空光](../reports/2026-11-21-door-light/README.md)

屋外の次の検証場所には、ランタンを吊った軒先を選ぶ。軒の内外に同じ石を敷き、降り始め、雨が続く間、止んだ直後、乾燥後を同じ視点と見下ろす角度で撮る。途中で灯りを回収し、石に映る暖色と雲間の日射を個別に確かめる。Photonでの材質・天空光の使い方と、Irisが渡す降雨・濡れの時間変化を比較資料とする。[Photon の雨天の材質処理](https://github.com/sixthsurge/photon/blob/main/shaders/include/surface/rain_puddles.glsl) · [Iris の天候入力](https://shaders.properties/current/reference/uniforms/world/)

固定視点の比較は個々の光路を調べるために使う。最終の判定には、テスト用の特殊な描画を外した通常設定の連続プレイと、ユーザーが手元で同じ操作を試せる配布版を使う。

1.7.0の配布ワールドでは通常のサバイバルで雨の夕方から夜を経て再び昼になり、軒先・木陰・坑道・池を19往復した。実時間20分51秒、保存した徒歩統計は3,334.82 m。松明を幹に付け直した回数も2回で一致した。晴天の木陰では松明を点けると昼の芝が約2倍、幹が約4.8倍の表示輝度になり、奥の白樺の明るさはほぼ一定だった。長期の対象には、プレイヤーが普段使う自然林での葉の透過、複数の灯りが重なる位置、雪境界での降水の切り替わりも含める。[雨と晴天の松明の比較](../reports/2026-11-21-rain-eaves/journey/run-7/oak-torch.jpg) · [実際の徒歩を約30秒にまとめた映像](../reports/2026-11-21-rain-eaves/journey/run-7/walk-highlights.mp4) · [通常ワールドの保存統計と連続映像の長さ](../reports/2026-11-21-rain-eaves/journey/run-7/complete.json)

### 通しで確かめる到達点

20分の一往復を最初の通し試験にする。その先の到達点は、自作の散歩道で再現した現象が、プレイヤーが選んだ自然地形や自分で建てた家でも同じように見えること。次の三場面を通常設定で遊べるところまで進める。

三昼夜の通し試験は、別々のシードで見つけた森・集落・雪の降る高地を含む、少なくともゲーム内三昼夜の通常プレイとする。森に松明を置いて遠出し、暮れた集落で窓や扉を造り替え、翌朝には地上から洞窟へ下りる。戻ってきたとき、残した松明は元の幹を照らし、新しく積んだ壁は西日とランタンをそれぞれの方向から遮る。途中で終了・再開も行う。雪や雨はその場所で実際に発生した場面から評価する。目立った光漏れ、暗順応の急変、光源の入れ替わり、長い描画停止は該当する時刻と映像を残して修正し、同じ操作で再確認する。

- **雨の森で火を置く。** 日差しを遮っている葉の下で松明を点ける。炎を向いた樹皮、手前の草、幹の反対側を歩いて見比べる。魂のランタンに持ち替えたら、雨粒と濡れた石にもその青い光が届く。幹や石壁が光源を隠す場所で色の変わり方を確かめる。
- **暮らしている家に灯りを持ち込む。** 色の違う二つの灯りの間で扉を開け閉めし、動物が横切ったあと、置いた灯りを一つ回収する。直射、室内の跳ね返り、窓を通る夕日について、それぞれが届く面を追う。チャンクを離れて戻り、さらに通常の保存・再読込をまたいで確かめる。
- **雨上がりの坑道から岸へ戻る。** 屋根の下の乾いた石と、軒先で濡れて光る石を通り、持っている光源を画面の外へ動かす。雨がやんでも残る照り返し、洞窟を出たときの露出、水際での反射のつながりを見る。晴天、自然に降雨する場所、雪の降る場所を含め、RTX 3080 Ti の実フレーム時間と目で見つけた破綻を同じ場面に記録する。

森の次の段階では、樹皮・草・葉を別々に調べる。晴れた木陰で幹の両側に二色の灯りを置き、片方ずつ回収し、葉の表と裏を回り込む。幹が一方を隠した面にはもう一方の色が残るか、葉越しの光が葉の厚みや隙間に応じて変わるかを通常のサバイバルで確かめる。雨の検証では木から離れる方向にも歩き、手前の明るい筋と遠くの降雨を見分けられるか確認する。

森の照明には二つの見方がある。木陰から葉を見上げたときは、陽を受けた葉の裏に色が届き、手前に丸太を挟むとその色が消える。松明を持って木を回り込んだときは、葉の隙間を抜けた光が奥の壁や地面に模様を作り、炎・葉・壁の距離に応じて輪郭がぼける。葉の奥に魂の松明を加え、一方を幹で隠し、もう一方を回収するところまで同じ配置で確かめる。次に屋内の窓格子と降雨時の水際で同じ操作を試し、材質、直射、反射、目の順応のつながりを長い往復の中で判断する。

一日の基準をMinecraftの昼夜が一周する約20分に置く。木陰で点けた松明を残して家へ入り、二色の灯りの間で扉を開け、暗い坑道を通って川へ出る。帰路では置いた灯りを回収する。屋外の晴天から降雨、雨上がりを同じ場所で見直す。通常のシェーダーで往復を連続収録し、室内外の切り替わり、チャンクをまたぐ地点、光源が画面外になる瞬間、再訪時の露出と色を確認する。区間ごとのフレーム時間と、まだ目に付く破綻を記録する。

夕暮れの家はこのうち、二つの独立した灯りと扉を目で追える段階まで進んだ。暗い扉を開けると白い床に暖色が差し、手前の石に当たる魂のランタンの強さはほぼ一定だった。初回の18場面で検証した光路と受光点を公開している。[配布版での同一画角の比較](../reports/2026-11-21-door-light/house-settled.jpg) · [受光点の測定値](../reports/2026-11-21-door-light/house-results.json)

### 自然生成の森と雪村で追う変化

1.8.0では、木陰の白樺に松明の色が届き、炎と白壁の間に葉を置くと輪郭のぼけた葉の模様が現れる。同じ森で松明を二本置き、片方を回収して洞穴まで行き、保存した位置から木に戻る操作を行った。別シード20261139には、トウヒの扉と二つのランタンのある家が実際に生成された。三昼夜の経路ではこの家と雨の降る平原を結び、途中で建材や光源を変え、遠出した後の同じ場所を見直す。[森の通常プレイの保存記録](../reports/2026-11-21-leaf-light/play/woodland-roundtrip/complete.json) · [雪村で実際に生成された家](../reports/2026-11-21-settlement-light/site/analysis.json)

雪村では通常のF3で雪原を確認し、家を出て150.84 m歩き、同じ降水の続く平原に着いた。別の場所から見ても同じ石が正しく濡れるか、建て替えた家に長距離の遠出を経ても元の照明が残るかを、この経路から発展させる。[天候を変えずに歩いた記録](../reports/2026-11-21-settlement-light/playable/village-to-plains/biome-crossing.json)

洞窟の光には、面で光る溶岩も含める。現行の松明は幹や石に対して光源ごとの遮蔽を持つ。溶岩はゲームのブロック光で周囲を照らしており、一マスの溶岩と壁の間に石柱を立てても、幾何的に直射のない領域に暖色がかなり残る。面積の違う溶岩に対して直射と岩からの間接光を分け、柱の後ろから一歩横に出たときの影、溶岩の縁を歩いたときの安定性も長い経路で確かめる。[1.8.0で一マス・九マスの溶岩を比較](../reports/2026-11-21-lava-light/baseline-180/lava-wall.jpg)

## Normal-play lighting objective, 2026-11-20

The aim is a walk from a sunlit clearing, under a tree with a torch, into a room lit by several lamps and out to a lantern beside water. The position, colour and obstruction of each light should remain legible while the player moves. The player should be able to change the lighting by placing a source or building a wall. Visual quality on the 3080 Ti takes priority over a fixed frame-rate floor.

| Scene | Observable result | Evidence |
| --- | --- | --- |
| A torch under a tree in daylight | The bark and grass facing the flame gain warm light while the tree continues to block direct sunlight | Matched images and separate solar receiver output |
| A room with multiple lights | Warm and soul lights can coexist. A stone divider stops the direct contribution on its far side. Coloured glass changes the transmitted colour. | Individual, combined, off and matching divider controls |
| A lantern by water | The surface reflects the lamp along the specular direction as well as reflecting illuminated scenery | Isolated reflected-light output and production image |
| Placing, removing and moving past lamps | The old source disappears. A world-stationary receiver keeps its illumination across a snapped grid boundary. | Cleared GPU fields, actual eye coordinates and a moving frame sequence |
| Playing in an existing instance | The normal shader and physics bridge run on the original Lab without the recorder. | Original-instance smoke run, save inventory and measured Minecraft frame intervals |

The [1.2.1 placed-light report](../reports/2026-11-20-local-light/README.md) records the room, forest, moving camera, display response and ordinary-instance evidence for this part of the objective.

The [1.3.0 carried-light record](../reports/2026-11-21-carried-light/README.md) covers both hands in an actual forest and mineshaft, third-person camera checks and the separate pillar/receiver experiment. The continuous forest-to-cave route, moving occluders and coloured diffuse bounce each have their own acceptance scenes below.

The [moving-cow preview](../reports/2026-11-21-mob-light/README.md) demonstrates a lantern projecting a real animal onto a wall, including a vanilla AI-driven walk. The [single-bounce reference](../reports/2026-11-21-indirect-light/README.md) supplies the expected diffuse transfer and two independent obstruction controls for the coloured-wall stage.

The longer-term destination is a continuous playable walk from a sunlit forest to a cave, through a lit building and back out beside water at night. During that walk both the player and light sources may move. These cases define the next stages beyond placed lights:

| Stage | In-game comparison |
| --- | --- |
| Carried lights | Walk with a torch, switch to a soul torch, change hands and put it away. Capture bark and a cave wall at fixed points, including the interval when a pillar crosses the light path. |
| Moving shadows | A moving mob crosses between a floor lantern and a wall. Follow the shadow on a fixed wall while the lamp, sun and sky stay in place. |
| Reflected light | Place a red wall and then a neutral wall of comparable brightness near a lamp. Observe a second surface around the corner with the direct path blocked. Include source-off and neutral controls. |
| Continuous play | Traverse the route in both directions at day, dusk and night. Review camera motion, exposure recovery at the cave entrance, local shadows and water glints in actual gameplay, with the 1440p frame-time trace alongside the footage. |

Each stage needs separately observed on/off evidence and a comparison in motion before a normal-play release can claim it.

## 2026-11-20 local normal-play release

The integrated shader, actual game images and remaining physical approximations are recorded in the [1.0 release report](../reports/2026-11-20-release/README.md). The following sections preserve earlier research checkpoints and their test-specific open questions.

## User-requested focus on 2026-10-11

The immediate goal is to resolve the user's reported issues. The subsequent
goal continuation explicitly requests implementation; investigation and source
comparison should guide changes rather than replace runtime verification.

- Establish the current sunlight implementation and remaining specification
  gaps; do not assume sunlight is entirely unimplemented.
- Explain why the Sun appears much smaller, checking angular size, projection,
  display resolution and presentation against actual runtime evidence.
- Investigate the unnatural sky seen from underwater, including refraction,
  total internal reflection and the transition around the sky window.
- Compare relevant upstream shader implementations using primary sources,
  separating observed implementation choices from proposed Aqualumen changes.

Record findings and acceptance criteria alongside changes. Treat the reported
appearance as unresolved until actual images and moving views are reviewed;
compilation or isolated numerical checks do not establish visual completion.

Active user goal, begun 2026-10-02. The user wants convincing realistic water and
sunlight, including reproducible physical phenomena where useful, on this RTX
3080 Ti. A dedicated client Mod is allowed. The original60-FPS floor was relaxed:
visual quality is the priority, with honest actual Minecraft timing evidence.
The instruction to continue toward the goal is not satisfied by calling the
existing prototype finished or by passing only its existing tests.

## Last verified ordinary-runtime baseline

The last ordinary-runtime verified experimental
pack is 0.6.0, ZIP SHA-256
`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`.
The retained 0.5.0 ZIP is unchanged, SHA-256
`88ff19eed363ff3d25287b3873ed7c0ac7b2ca654074e0365d510fedd07c859d`.
The frozen0.4 implementation is commit `6dd4e5a`, ZIP SHA-256
`5c456e84dd97ea76dd6f3ee44a78061d7d9cfe89c4738845543180e2d7bb8069`;
its comparison images and distinct1440p timing evidence remain retained.
The previous 0.3.3 baseline, commit `a81c7ae`, remains the retained comparison
artifact with SHA-256
`ff81efa32c96f3b1c2c76c1c55fe6e32ed29f1344e67a239afeeccca980583e5`.
Its eye-coordinate and underwater directional-sky fixes are retained and must
not regress.
Physics bridge 0.2.0 and its persistent local wave solver are already installed.
These are a working foundation, not proof of the full visual goal. Normal-play
settings were restored byte-for-byte and development instrumentation disabled;
the user's ordinary-account world runs 0.6 and is paused at the recorded handoff.
The [0.6 verification](../reports/2026-10-02-v0.6.0/VERIFICATION.md) and
[independent final-handoff addendum](../reports/2026-10-02-v0.6.0/INDEPENDENT-AUDIT.md#final-saved-state-and-ordinary-handoff-addendum)
record that point-in-time evidence. This runtime handoff
does not complete the rendering goal, which remains active, not achieved.

## Requirements and completion evidence

- Water should look natural across shallow/deep water, shorelines, above/below
  the surface, changing view angles, lighting, rain and moving contacts. Remove
  demonstrated false-hit/fallback discontinuities; do not merely desaturate an
  incorrect geometry path. Judge original real Minecraft images and motion,
  backed by controlled production-renderer tests for the causal corrections.
- Sunlight, sky/cloud illumination, water highlights, shadows and underwater
  illumination should form a coherent light-transport model, with visible depth
  and plausible daytime/sunset/night variation. Check reflected/transmitted
  sky and direct-light source consistency rather than only isolated formulas.
- Physical effects must be described accurately: optical laws and transport,
  dispersed wind waves and persistent contact-wave dynamics are distinct from
  mass-conserving water movement. Extend useful physical effects when the visual
  goal requires them; do not call a decorative animation a fluid simulation.
- Verify temporal appearance: moving-camera water highlights/refraction and
  contact propagation must not be judged solely from one still screenshot.
- Preserve the ordinary user's saves, instance settings and assets; use only
  UUID-guarded disposable fixtures for automated camera/terrain operations.
  Preserve old releases and restore safe ordinary play after validation.
- Verify every introduced shader/module on real NVIDIA GL, all retained
  regressions, Minecraft/Iris activation without fallback, and affected natural
  scenes. Record raw intervals and visual limitations without an FPS guarantee.

Full-goal completion requires inspecting the final actual runtime evidence
against all requirements above. Finishing a vertical slice or documenting a
known visual flaw does not by itself establish completion.

## Current implementation and validation progress (not full-goal completion)

The first0.4 water slice separates opaque direct-Sun receiver radiance from
total shaded color, snapshots it before translucents, and focuses only a
confirmed refracted receiver's direct component. Production-main RTX3080Ti
tests establish zero-Sun invariance (former maximum RGB change0.0289524,
now0), red-only positive focusing0.0107598 with unchanged green/blue, and
zero proxy focusing (formerly0.000158489). Real terrain/deferred MRT copies
also match and remain immutable after later producer-buffer writes.

The0.3.3 underwater directional-sky/Fresnel/TIR/cave/eye tests are retained.
The continuous-bed production test now verifies a vanishing handoff change:
the former0.066329 RGB jump across approximately0.00004m becomes0.00000570714
in the preserved failing interval. Above-water topfaces finish a fixed solve
and blend separately transported hit/proxy radiances by numerical reliability;
underwater/vertical-face early-return policy stays unchanged. This does not
prove every discrete/occluded bank silhouette continuous.

Underwater composite zero-Sun variation0.0769311 now becomes0, positive red-only
direct attribution remains0.0285025, and nearer-depth layers reject behind-layer
caustics under both NEAREST/LINEAR input filters. Raw same-pixel depth snapshots
are paired with C8, before one eye-leg attenuation. Rejected-foreground-bank
controls and the final full native suite pass on RTX 3080 Ti OpenGL 4.6; these are
production-fixture results, not Minecraft timings or a full natural-shore proof.

The installed 0.4.0 pack completed 16 recorded Minecraft/Iris compatibility
scenes, including natural coast/river/ocean, underwater views, moving view,
scripted boat contact, cave water, glass and Nether/End. Four 0.3.3 comparison
scenes are also retained. The
[independent exported-data audit](../reports/2026-10-02-v0.4.0/INDEPENDENT-AUDIT.md)
verified 20 strict PNGs and all 18,506 raw intervals (3,889 before / 14,617 after),
pack identities and recorded scene metadata. Minecraft records GL 3.2 while the
native harness records GL 4.6; do not conflate the two contexts or evidence types.

The four saved A/B mean FPS values are lower in 0.4.0. Ocean-day and upward-near
water differ in capture-time focus (before focused, after unfocused), so those
changes are not pack-only causal comparisons; coast/river remain focused. All
candidate P99 values fit 16.667 ms, but dusk/night each contain one slower interval,
with worst 21.775271 ms. The strict 60-FPS floor was relaxed, and no all-frame floor
or arbitrary-world performance guarantee is claimed.

Natural images still show strong shallow-water cyan and jagged/discrete shore
transitions. The controlled continuous-bed correction does not establish that
those visual defects are solved. Three replacement0.4 full-window1600x900 clips
were recorded and reviewed: image coverage is valid, but natural boat/wake motion
is not accepted. Scripted boat translation contains a sharp relative-geometry
change and the wake is mostly outside the forward view; it is not vanilla rowing.
See the preserved0.4 visual audit and temporal-video audit. These separate
recording workloads do not replace1440p performance measurements.

The0.5 incident-Sun slice adds the mean-horizontal-interface Snell beam path,
exact Fresnel entry loss and RGB Beer attenuation to the paired raw direct-Sun
component, before the existing separate outgoing attenuation. Three genuine
production-main RED/GREEN increments prove incident-depth response, absolute
normal-entry energy and above-water two-leg response. Zero-source/non-Sun
controls and all retained regressions pass. C8 remains immutable air-lit source
attribution, not a pre-attenuated source. This is not arbitrary-normal/bent-shadow
transport, a water-membership proof or a depth-dependent in-scattering solution.

The0.5 [16-scene real-view run](../reports/2026-10-02-v0.5.0/real-view/run.json)
and [independent audit](../reports/2026-10-02-v0.5.0/INDEPENDENT-AUDIT.md) verify
16 complete1600x900 PNGs and24,701 raw positive intervals, active88ff19 pack and
all16 focused captures. The unmodified1440p report verifier deliberately rejects
this resolution; this is a separate quality/compatibility audit, not a claimed
1440p benchmark. The [visual audit](reviews/codex-v0.5-visual-audit.md) finds the
cyan/serrated shore issue persists;0.5 temporal naturalness is unverified.

The [ordinary handoff](../reports/2026-10-02-v0.5.0/ordinary-handoff.json)
verifies a fresh normal-account launch with0.5/physics0.2.0 and disabled benchmark
controls,1600x900/cap120 restored options and a paused native game view. Ordinary
world automation was not used; natural saves resume after normal launch. The
instrumented TEST-client shutdown stall remains unresolved; its cause is not
established or claimed fixed. Continue controlled shore optics diagnosis, natural motion,
coherent spatial cloud shade and calibrated sunlight. Cloud/light and other
full-goal requirements remain open.

At the initial post0.5 checkpoint, the [stepped-shore diagnostic](../reports/2026-10-02-shore-diagnostic/README.md)
ran deterministically through actual production main, with a closed bank,
independent depth/color inputs and positive reflection/bed controls. Initial
large jumps were fixture-boundary/palette changes, not shader REDs. A qualified
same-input-face/color/coverage bracket responds to optical-normal/fragment-depth
ablations but not environment-only SSR. Actual refracted receiver identity and
source continuity were unproven, and other switches persisted. This evidence
narrows the next causal investigation; it does not justify a shipping shortcut
or a claim that natural shoreline artifacts are fixed. Installed0.5 was unchanged
at that diagnostic stage; the subsequent bounded0.6 correction is recorded below.

The initial [solar-radiometry source review](reviews/codex-solar-radiometry-plan.md)
also identifies an actionable disk/direct-beam energy and HDR-range mismatch.
Its source-derived angular integrals are not a fresh GPU result; the proposed
actual terrain/deferred-main unity test was pending at that review. Its subsequent
RED/GREEN results are recorded below, rather than attributed retroactively to the
design review. The original60FPS floor remains relaxed; real timings are
observations, not that old acceptance gate. Full solar/cloud transport coherence
is not established by the bounded correction.

## Proven 0.6 checkpoint and unmet requirements

The 0.6 above-water topface search retains a visible deep receiver that the 0.5
fixed-point solve skipped while alternating between depth cells. Across the
same 48-micrometre perturbation, the public-main tagged-green response loss
`0.100883→0` becomes `0.100884780288/0.100881353021`: difference `3.42727e-6`,
within the unchanged independent physical/one-depth-pixel bound `0.001669252223`.
Foreground-bank, viewport, surface and residual guards remain; underwater and
vertical-face iteration policy is unchanged. The
[causal review](reviews/codex-shore-causal-review.md) and final-current
[native suite](../reports/2026-10-02-v0.6.0/native/v0.6-full-native-check.log)
establish this bounded correction, not natural shoreline acceptance.

Separate genuine production terrain/deferred-main clear and rain RED/GREEN
increments compare actual receiver beam irradiance with the disk's independently
integrated raw sky radiance. Clear ratios approximately `0.001357` become
`1.000123–1.000527`; rain-only ratios approximately `6.667` become
`1.000007–1.000205`. The angular-support/coverage normalization and existing
weather factor now agree within the unchanged 2% gate. Native 1600x900 and 1440p
FOV 60 cases, including one 0.37-pixel 1440p phase shift, also pass. Only C0/C4
are promoted to 32F; a deliberately half-float diagnostic clips at 65504 and
fails energy coherence. The old underwater Sun-presence upper bound was
recalibrated to the declared source units, without a shader change for that
oracle correction. See the [solar review](reviews/codex-solar-coverage-review.md)
and separately retained native failures/positive/negative controls.

The completed 0.6 [actual Minecraft run](../reports/2026-10-02-v0.6.0/real-view/run.json)
contains 16 active, nonfallback 2560x1440 scenes and 14,909 positive raw intervals.
The unchanged 1440p reporter accepts it; independent audits validate all PNGs,
identity/eye/contact metadata and recomputed timings. All captures report focus;
that does not establish continuous focus throughout every interval. For the 14
overworld/water/cave/glass scenes, mean FPS is 126.5–196.9 over 5-second samples;
worst across all 16 is 10.601779 ms. No new-chunk traversal or general FPS floor
is established. Actual Iris initialization observes C0/C4 main/alt RGBA32F,
the other queried targets RGBA16F and correct frame/LUT dimensions; this is an
allocation snapshot, not HDR pixel readback or an Iris energy-integral test.

The [0.6 visual audit](reviews/codex-v0.6-visual-audit.md) still finds cyan/mint
shallows, jagged dark/clear shore bands and stylized reflection ribbons. The
underwater curved sky window and cave/glass/dimension compatibility remain,
without an obvious catastrophic regression in the reviewed stills. Different
resolution/phase 0.5 images are qualitative comparisons, not controlled pixel
causality or a timing A/B. Moving/boat stills and measured contact input do not
accept temporal highlights, refraction, wakes or natural vanilla rowing.

The [ordinary handoff](../reports/2026-10-02-v0.6.0/ordinary-handoff.json) records
fresh normal-account 0.6/physics 0.2.0 activation, benchmark controls disabled,
original options byte-restored at 1600x900/cap 120 and a verified pause menu.
The before/after saved-state audits find 390 approved reserved TEST cells AIR
and no journal, not whole-world/entity integrity. TEST Save/Quit stalled again;
scoped termination followed the cleanup checks. A clean shutdown or defect fix
is not claimed. Ordinary saves naturally resume after normal relaunch.

Still unmet: natural-shore color/path handoff and motion acceptance; coherent
spatial cloud shadows and convincing cloud shape; arbitrary wet-receiver normals,
bent shadows, water membership and depth-resolved in-scattering; general
refracted-radiance/index-squared (`L/n²`) and étendue transport, including nonlinear
underwater disk coverage. The separate bottom-beam flux tests do not prove that
radiance convention or authorize a compensating factor. Horizon/large-off-axis
coverage, rough-water solar quadrature, empirical weather coupling and Moon
normalization remain bounded/approximate. **The full goal remains active.**

## Execution sequence

Post0.6, the [0.7 native-only candidate](../reports/2026-10-02-v0.7.0/WORK-IN-PROGRESS.md)
corrects a separately qualified sampled-facet SSR source loss: an existing
overshoot cutoff was narrower than the last actual march segment. Positive
source retention, off-ray/submerged tag negatives and all retained native tests
pass. Only above-water upper-interface crossing width changes; ordinary runtime
remains0.6 and candidate natural-view acceptance is pending.
At that 0.7 checkpoint an independent remote-camera-ray/local-bed fixture also reproduced a source-gain
change despite identical water geometry and local depth, in both frozen0.6 and
the0.7 candidate. That genuine optical-depth RED was unresolved there. The next
architecture needed shared actual local bathymetry between geometric and optical
waves, without shipping a global depth override to hide it. Those observations
do not certify all shore discontinuities or complete this goal.

The [0.8 native checkpoint](../reports/2026-10-02-v0.8.0/WORK-IN-PROGRESS.md)
implements the shared local-column field, its depth-gradient wave term and an
explicit coarse-facet fallback. The original remote-depth source-gain RED now
passes with actual valid fixture data; missing-input/mixed-primitive, physical
shallow/deep and derivative controls also pass. Physics0.3 supplies loaded-chunk
columns with a bounded cache, but is not installed or live-sampler validated yet.
An independently qualified new visible-bed condition exposed a further loss
from near-converged bisection/confidence mixing. A same-depth-reprojected proposal
fixes it while retaining all final guards; both NEAREST/LINEAR variants and the
retained native suite pass. These are production-fixture results only. Ordinary
runtime remains0.6/physics0.2; natural-coast/motion, cloud and full physical goals
remain open. Do not substitute these native passes for actual Minecraft quality.

The subsequent [0.8 isolated runtime checkpoint](../reports/2026-10-02-v0.8.0-runtime/README.md)
now proves actual named-sampler/storage/readback on the RTX3080Ti Minecraft
client, after a real-Fabric-metadata failure was fixed in test-only observer0.3.6.
The filled64² field has4096 finite valid columns and conditional saved-floor
corroboration; same-frame absolute-camera and final-fetch attribution remain
limits. Actual ocean/coast captures still show cyan/mint shallows and jagged
bands: the visual goal is not accepted. No new1440p benchmark or motion-quality
claim is made. Normal0.6/physics0.2/configs are restored, benchmark disabled and
the ordinary world is reopened paused. All five requirements below remain open.

1. Diagnose shallow-water cyan and shore discontinuities from actual production
   inputs. Test one reproduced behavior, implement it, and repeat. Prefer correct
   receiver/path/lighting provenance over cosmetic compensation.
2. Improve water's depth-dependent appearance and receiver illumination based
   on the findings, with clear optical assumptions and real-view comparisons.
3. Improve cloud shape/lighting and coherent sunlight/highlight appearance.
4. Validate moving views, waves/contacts and day/weather/dimension compatibility.
5. Audit the full visual goal and continue any unmet requirements. Do not mark
   the goal complete from code compilation or warmed-view timings alone.

Implementation and independent review are Codex work unless a genuine external
model invocation is explicitly recorded. Do not misattribute team agents to
Claude Opus/Sonnet.

The subsequent [shore-source atlas checkpoint](../reports/2026-10-02-shore-attribution/README.md)
separates transmission, reflection, confidence and raw opaque source color in
three actual captures. The coast's camera-site one-block label does not describe
the full viewport: an independent saved-bed profile confirms rapid deepening.
This rules out declaring every4–9m path erroneous merely from the site label.

The [world-coordinate shore checkpoint](../reports/2026-10-02-shore-world-r3/README.md)
adds actual same-frame FINAL-sampler RGBA32F reads at16 native coordinates,
independent program identity and verified11-state restoration. Explicit water-main
MRT payloads pair surface, transmitted direction, returned receiver/kind, four
path values, original opaque position/local depth and normal/Fresnel. Thirteen
qualified water points contain four hits/nine proxies; three are cleared sky.
The corresponding earlier PNG is not the same wave phase as the raw snapshot.
Saved full-cube ray traversal gives conditional real-terrain comparisons: three
accepted paths agree closely with first-floor distances, one accepted shore-edge
point differs, and proxy paths can be either shorter or longer than the first
saved intersection. Local vertical depth alone is not that ray distance.
The observer's missing-final-uniform/full-geometry flags remain false. No natural
visual fix, new shipping version or full-goal completion is claimed. The next
correct seam is an independently first-visible-bed-qualified production-main
source response, separating exploration seed from the unchanged miss proxy.

The [0.8.1 bounded correction](../reports/2026-10-02-v0.8.1/README.md) now separates
that exploration seed from the unchanged original-view miss proxy. A confirmed
local column supplies only a search hint; bank/viewport/surface/residual checks
remain. Actual original production-main NEAREST and LINEAR old-source REDs lose
the same independently qualified visible first shelf when only a remote floor
changes; the candidate retains its source/path and independently bounded absolute
Beer/Fresnel gain. Current archives also preserve neutral/tag mode0/2/3 and
repeat float images. All retained NVIDIA native tests pass before the actual
six-scene Minecraft run, which activates0.8.1 without fallback at1600x900.

Natural coast/river images still show broad cyan/mint and pointed dark bands;
cloud shape remains repetitive. Upward underwater stills do not show the old
rectangle/double-map seam but retain strong round curvature. Neither desired
underwater appearance nor motion naturalness is accepted. The ordinary configs
and physics0.2 are byte-restored after bounded TEST termination; current lifecycle
evidence distinguishes restoration-before-relaunch from an actual paused handoff.
The repeated TEST Save/Quit stall is not fixed. All full-goal requirements remain
open. The next causal slice enables real public wave geometry in the qualified
first-visible-bed probe, without replacing it with a cosmetic color adjustment.

That fixed [nonzero-wave slice](../reports/2026-10-02-v0.8.1/native-waves/WAVES-AUDIT.md)
now passes at phase1.25/WAVE_HEIGHT0.12/pixel65,48 with original VS geometry and
independent first-surface/source bounds. The first raster-envelope failure is
retained as INCONCLUSIVE, not shader RED. This is one NEAREST/explicit-triangle
fixture, not actual Sodium topology, wave-spectrum or natural-shore acceptance.

The completed [0.8.2 development checkpoint](../reports/2026-10-02-v0.8.2/README.md)
corrects an actual same-world receiver direct-Sun change tied to the observer's
cloud cache. Qualified fixed P/Q production-main RED/GREEN tests retain positive
spatial cloud extinction, absolute C5 bounds and actual deferred C8 retention.
All retained native tests pass, including the fixed nonzero-wave first-bed probe.
Actual nonfallback coast/river/ocean Minecraft captures at1600x900 recompute
mean94.42/91.07/67.25FPS; ocean1%low53.01 shows the new integration cost, not a
60FPS floor or1440p guarantee. Cyan/mint shallows, jagged bands and artificial
clouds remain; no new underwater or motion capture is recorded. Actual Iris C7
storage is observed, not a named-sampler/cache-pixel readback proof.

TEST Save/Quit again stalls; scoped TERM follows saved390-cell AIR/no-journal
checks. The exact test processes are absent and original configs are byte-equal
to pre-test backups, ordinary0.6/physics0.2 selected and instrumentation
recoverably disabled. At the restoration-before-relaunch checkpoint no fresh
ordinary paused handoff is claimed. Ordinary saved files match the fresh
post-user-play backup; no ordinary-world restoration or automation occurred.
The full goal and all remaining natural-appearance/motion/physical requirements
stay open. The next qualified slice checks the known direct receiver component's
[exiting radiance units](reviews/codex-water-sun-radiance-plan.md), not blanket
frame dimming, empirical desaturation or a redefinition of visual acceptance.

The subsequent [0.8.3 checkpoint](../reports/2026-10-02-v0.8.3/README.md)
corrects the known direct-C8 receiver component's water-to-air directional
radiance units. Two qualified original-main old-source REDs produce roughly
1.7769 times the independent source response; the direct-only exit correction
matches all RGB bounds, with serial native/cloud/nonzero-wave regressions passing.
This is not global darkening or a calibration of ambient/proxy/scattering paths.

Six actual focused1600x900 views activate exact0.8.3 without fallback. Raw3009
integer-ns intervals are independently recomputed; mean coast91.98/river88.81/
ocean66.15/underwater-up118.42–118.52FPS are warmed observations, not1440p or a
60FPS floor. Three actual submerged near/deep/tilt eyes have no visible old
rectangle/double sky map, but strong round curvature and dark outer regions
remain. Cyan/mint shores, pointed dark bands and artificial clouds remain too.
Natural appearance and motion are explicitly unaccepted.

After sampling, actual terrain/water named C7 sampler units, existing target
identity, two reserved-row cache texels and all11 restored caller-state fields
are observed. This closes allocation-only evidence for prepared inputs, not
specific fragment execution or same-frame producer freshness.
TEST Save/Quit still stalls; bounded saved390-cell AIR/no-journal checks precede
and follow scoped own-process TERM143. Original configuration bytes and ordinary
saved-file equality are verified before relaunch, with no ordinary restoration
or automation. Normal0.6/physics0.2 is then actually reopened and paused; later
Iris timestamp-comment regeneration is distinguished from byte restoration.

The full goal remains active. The next discriminating underwater seam is a dense
flat original-main directional marker map compared with independently projected
Snell/TIR geometry, then wave-normal/rim and offscreen-reflection missing-source
tests. A physical round window must not be erased merely to pass a cosmetic
image criterion. Shore/cloud/motion and broad physical/compatibility work remain.

The subsequent [underwater angular checkpoint](../reports/2026-10-02-underwater-angular/README.md)
captures the actual uploaded water-program matrices and verifies a native-only
flat directional map with an independently qualified positive reflection chain.
Serialized executions agree byte-for-byte; the captured-view angular subcheck
is positive but its full reflection qualification remains INCONCLUSIVE.
Natural wave-rim/dark-exterior appearance is not accepted. A separately qualified
near-reflector regression is the next implementation slice, not a claim that
the original natural image has been fixed.

Normal-account disposable V2 Save/Quit now cleanly saves all dimensions and
exits without a signal under the unchanged candidate/Mods, providing an effective
launch-identity workaround for the name-only TEST override. Runtime host-profile
causation is not proven. Ordinary0.6/physics0.2 was reopened paused at17:40:51;
its next normal Save/Quit at17:55:58 also cleanly saves all dimensions and the
owned client exits0 at17:56:24 before new GPU work. No ordinary-world automation
or restore occurred. This lifecycle evidence does not complete the visual goal.

The following [0.8.4 checkpoint](../reports/2026-10-02-underwater-reflection/README.md)
fixes a qualified first-visible0.3m underwater reflector missed by the previous
point's wrong projected-depth comparison. Original-main actual input readback,
independent lower gain/path bounds, real native RED→GREEN and a nonvacuous
black-first/red-background negative support only this local repair. All retained
native regressions pass. An actual Iris annotation parser failure in a diagnostic
pack is retained and corrected with four explicit clear-colour components;
public-ZIP CPU RED→GREEN and actual nonfallback loading are separately checked.

Three actual same-invocation atlas views and five shipping0.8.4 smoke views
remain visibly unnatural: dark water exterior/wrinkled round rim, cyan shores,
pointed jagged bands and procedural clouds persist. Atlas displays unknown
local-column and SSR-miss flags, despite ready CPU bathymetry; raw C9–C11
allocation/binding/readback is not proven. A known-column-only facet ablation
is not run because it may be inactive. The next causal seam distinguishes actual
raw column, vertex unknown and upward/downward-face classification without
changing the refractive index or forcing a known flag.

Matched-profile disposableV2 clients cleanly save/exit0 without signals; saved
390-cell AIR/no-journal checks remain positive. Ordinary saved files match the
fresh post-save backup before relaunch; no world restore/automation occurs.
Original configs and ordinary0.6/physics0.2 are restored, test instrumentation
recoverably disabled, and the actual ordinary game is reopened/paused at22:10:28.
Candidate0.8.4 is installed but not selected. The broader objective is unfinished;
neither the local repair nor the short1600x900 captures count as visual completion.

The [0.8.5 reversed-top checkpoint](../reports/2026-10-02-underwater-reasons/README.md)
now distinguishes the actual raw local-column query from the contributing-vertex
guard:16 actual FINAL water texels observe a negative top input normal, rawKnown1,
unknownWeight near1 and finalKnown0. The original production VS/FS native
same-top/winding RED has0.056715965m vertex displacement difference and0.14526148
optical-normal difference; the candidate gives exactly0 differences with all
qualified input, positive-wave, whole-C0 observation and repeat checks intact.
Negative faces use the local-column wave only when confirmed; fragment promotion
also requires every contributing vertex. A4m-column bottom and invalid-column
backtop remain undisplaced/unknown/unpromoted in separate bounded controls.

The corresponding after-Iris named-sampler readback observes unknownWeight0,
rawKnown1 and finalKnown1 at all16 points, with actual RGBA32F targets and restored
caller state. PNGs are different frames/phases, not a controlled pixel-difference
oracle. All retained native checks pass; five shipping1600x900 real scenes load
the new candidate without fallback. Actual stills remain visibly unnatural:
cyan/mint shallows and jagged dark bands, distorted submerged round-window rims,
dark exterior and procedural clouds persist. Motion is not accepted. Short
captures do not establish a1440p result or an all-frame60FPS floor.

The normal0.6 baseline is not replaced by this development candidate. A further
thin-bottom/topology boundary is not covered by the4m negative: the existing
surface-height tolerance is0.12m. Pinned Sodium bottom planes and minimum top
corner heights offer a separate local discriminator; test that next rather than
globally narrowing the shared column tolerance or claiming every bottom safe.
Offscreen reflection provenance, natural-shore transport, cloud appearance,
temporal contacts and all broader physical/compatibility goals remain open.

The [0.8.6 thin-bottom checkpoint](../reports/2026-10-03-thin-water-topology/README.md)
now reproduces the .12m same-height alias on a supplied1/9 column and pinned
Sodium bottom. Original VS displacement1.5725mm and final-known/top promotion
become zero displacement and rejected promotion with ONLY a negative-known
VS fractional-height discriminator. Shared tolerance, FS, wave/optics/transport
and positive-top fallback are unchanged. Same-binary native RED→GREEN,25
opposite-winding top envelope controls and5 front-facing air-side bottoms pass;
all retained native regressions pass. Primary bytecode provides a possible
slime-floor counterexample; live thin-sheet meshing is NOT reproduced. The
guard is bounded to pinned vanilla topology/normal heights, not arbitrary Mods.

Five actual900p shipping views load0.8.6 without fallback under exact disposable
V2 guards, with independent PNG/pose/raw-ns audit. Severely undulating submerged
sky rims/dark exterior, cyan/mint shores/jagged bands and procedural clouds
still fail visual acceptance. Short capped frame observations do not establish
1440p, a guaranteed FPS floor, motion or completion. Both owned clients save
all dimensions and exit0 normally; persisted390-cell AIR/no-journal cleanup and
ordinary saved-tree identity before relaunch pass. Original configs are restored,
test instrumentation recoverably disabled, and ordinary0.6/physics0.2 is
actually reopened/paused at05:03:29. The candidate is installed but not selected.
Unknown/mixed-top symmetry, coarse-geometry/optical-facet consistency, physically
grounded offscreen reflection, shore/cloud/motion and the FULL goal remain open.

The [resolved-normal diagnostic](../reports/2026-10-03-underwater-resolved-normal/README.md)
retains the same factor4 geometry but lowers only known underwater optical wave
detail. Actual deep-water fine folds/holes visibly decrease; near/tilted rims
change and retain ripples, while the dark exterior remains. Seven bounded
native height/slope checks pass, but overall v2 stays strict RED for tiny air
bitwise differences; v1 remains INCONCLUSIVE. Neither the cutoff nor appearance
is adopted. The normal0.6/physics0.2 runtime was actually reopened paused.

The [residual-interface experiment](../reports/2026-10-03-water-residual-interface/EXPERIMENT.md)
now implements an unused-in-production TEST helper and pinned diagnostic-pack
hook: resolved mean plus declared independent missing-power directional slope
covariance, Gaussian9-node projected-area quadrature and per-ray Fresnel/TIR
source evaluation. The same actual4stage native binary first fails on the
pass-through stub, then passes with the implemented operator. Seven directional
source responses and constant-source C0 consistency, passive/repeat/negative
controls are independently audited. This is concrete optical integration
progress, not full dielectric/physical energy, quadrature-convergence, actual
Iris or natural/temporal acceptance. The finite-node model excludes unobserved
masking/offscreen geometry and can fall back discontinuously on rejection;
critical-angle, zero-residual and covariance-rejection tests remain required.
Existing frozen failures and shipping sources are preserved. The full objective
and shore/cloud/light-unit/motion requirements remain active, not achieved.

The same residual slice subsequently retains an actual invalid-covariance
guard RED, then passes the unchanged boundary binary after strict negative
Schur-remainder rejection; zero residual and nonzero all-TIR controls pass.
A separate double arithmetic oracle checks12 selected points, not a critical
sweep or energy test. The original tracer and STORE-only observer passivity
checks pass with the corrected helper. Actual Iris CONTROL/TEST near/deep/tilt
captures and later selected FINAL readbacks confirm48 applied TEST points;
no-fallback and four linked TRANSLUCENT stages/arity3 are observed, not exclusive
water draws or node invocation count. The actual inactive C13–15 descriptor
tooling RED is preserved before its bounded test-first parser fix. Root23 CPU
tests pass. Appearance is not adopted: separated bright sun points and rim
striations require angular-source/critical-boundary diagnosis and refinement.
Normal0.6/physics0.2 has been restored and freshly viewed paused again; old
strict RED and frozen packets remain unchanged. The full objective stays active.

The [angular-source diagnosis](../reports/2026-10-03-water-residual-angular/README.md)
now reproduces bright-point splitting in actual native water main with a
derivative-free narrow Gaussian source, on the same5,025 known/eligible/valid/
applied pixels across GH3/GH9/GH17 and four source controls. Original geometry,
covariance, transport and source units are fixed. Sparse sampling is supported
without stock solar derivatives or applicability switching in this bounded
reproduction; neither is excluded for natural critical/rim/native-Sun cases.

Independent double finite-rule arithmetic matches156/156 selected actual
samples (original84 plus separate source-positive72). Continuous finite-window
integration qualifies34/39 reference cases; the original five tiny narrow
references stay INCONCLUSIVE. At the bright pixel, actual GH3 red0.09712414
contrasts with the qualified reference0.01305445; at the center GH3 nearly
misses reference0.00862005. GH17 is not a converged truth or monotonic cure.
Narrow component counts5/3/4 versus broad1/1/1 are descriptive, not adoption.
This turn is numerical diagnosis/tooling progress, not an implemented optical
fix, new Iris scene, energy/reciprocity proof or full-goal completion.

Normal0.6/physics0.2 is actually reopened and freshly viewed paused10:35:21 after
all native work; original options/benchmark bytes and prelaunch ordinary-save
identity pass, with no world restore or camera/time/terrain automation. Iris
only regenerates its timestamp comment. Shipping sources and old strict
failures remain preserved. A light-domain sharp-source integral with verified
inverse Snell/Jacobian and unchanged stock solar units is the next bounded
correction, followed by actual Iris/rim/motion qualification. All broader
natural shore/cloud/physical/contact requirements remain active.

A separate [CPU inverse-Snell checkpoint](../reports/2026-10-03-water-residual-light-mapping/README.md)
adds the qualified exact-unit light-to-normal mapping and slope/solid-angle
Jacobian. Two public-API wrong-implementation REDs become GREEN; six CPU tests
pass, with five finite-difference determinant errors at most3.009e-9. This is
concrete mapping implementation progress, not a Gaussian/source integral,
binary32-input/GLSL, physical-energy, native Sun or natural-rendering fix.
The actual-main source-integral RED→GREEN and subsequent Iris/rim/motion checks
remain required. Shipping and ordinary-runtime assets are unchanged.
The same ordinary client is freshly re-viewed paused at10:51:58 after these
CPU-only checks; no subsequent native GL or ordinary-world automation occurs.

The [passive native-Sun reason checkpoint](../reports/2026-10-03-water-residual-sun-reasons/README.md)
now adds TEST-only first-failure/group accounting without changing physical
predicates or shipping selection. Root21 new CPU tests and retained native
checks pass. Independent full native replay verifies270 finite maps,135 exact
repeat pairs and175 comparisons with passive difference0. However actual Iris
near retains the unchanged minimum4 **negative** gate:2/16 applied; first
failures facet/critical10, reflection-hemisphere2, reconstruction2. Native-wide
reflection dominance does not generalize to that selection. No reflected-only
patch is adopted; exact binary32 forward-support/critical-boundary replay is
the next seam, not tolerance or presentation tuning. Current Iris reasons do
not contain raw n/v/Sun/targets and cannot prove which compound subpredicate
caused those ten failures. Optical, AA, full-frame visual, motion and shipping
acceptance remain false. Normal0.6/physics0.2 is restored and freshly viewed
paused14:59:53, with no ordinary backup restore or later native GL. The full
realism objective remains active, not achieved.

The [stable inverse-Snell checkpoint](../reports/2026-10-03-water-snell-boundary/README.md)
now implements a TEST-only pure GLSL node, with supported-critical numerical
RED→GREEN on the actual RTX 3080 Ti. All325 fixed inputs pass independent and
root replay:307 supported/18 absent, max XYZ error2.974e-8 and T/J relative
error5.267e-8. Root23 new CPU tests and retained11 native program pairs pass;
six derived48-node interior source-response sums match both references within
unchanged bounds. The old node rejects18 positive critical inputs;22 additional
saved-input strict-vector failures are not old whole-wrapper defects. Raw view
and eta remain fixed, generated-target direction semantics are explicit, and
the guarded inverse uses FP64 internally without changing production admission.
It is not included by water main/cap or installed into shipping. The previous
actual Iris2/16 negative gate and legacy full/base tilted-fixture exclusion
remain. Actual-input attribution, TEST main integration, support/visibility,
critical/rim convergence, pixel-AA, Iris/motion, performance and energy proofs
remain required. Normal0.6/physics0.2 is reopened and freshly viewed paused
15:48:48; no ordinary comparison copy was restored or later native GL run.
This is concrete bounded optical-arithmetic implementation, not fish-eye or
full-goal completion.

The [prepared-view reuse checkpoint](../reports/2026-10-03-water-prepared/README.md)
now proves a TEST-only local view/eta integer-context hoist on actual RTX3080Ti:
376 fixed standalone inputs preserve classes/rawbits/six interval triples;
the corrected independent reader and root replay verify every role/repeat.
Two actual original-water-MAIN runs pass6 fixed scenarios with zero binary32
bit differences, unchanged geometry/TES/depth/optical output and full48 direct
target/view/class/count ledgers. Each independent audit verifies648 capture/
depth maps,1,728 node maps and396,294 full-view ledger pixels. Predeclared
9-pixel arithmetic verifies1,440 both-mode records/720 unique raw inputs,
not every-pixel physical truth. All called MAIN nodes are supported: standalone
absent/unknown proof does not close MAIN or Iris branch coverage. Per-node
all48 optical neutrality retains producer exact hashes, not independently
recomputed per-node C0/depth/TES raw archives.

Draw-only native ABBA timing shows3.62–11.57% lower active medians over the
two runs; controls have small mixed changes, central absolute medians drift
23–24%, and outliers remain. This is not Minecraft FPS, universal/significant
speedup, a60FPS floor or ordinary-pack acceptance. No pack/Mod/config was
installed for this slice. All retained native checks pass; corrected auditor,
host-guard, timing-state and orchestration failures stay recoverable. The
ordinary comparison save is never restored. Normal0.6/physics0.2 is actually
reopened and freshly inspected paused20:48:38, with TEST entry points disabled
and no subsequent native GL. Next is reversible TEST integration/actual Iris
qualification, then remaining optical-band/rim work. Shore/cloud/transport/
energy/motion and the FULL realism goal remain active and unachieved.

The [prepared actual-Iris checkpoint](../reports/2026-10-03-water-prepared-iris/README.md)
now packages that local view/eta hoist reversibly and qualifies new TEST physical,
reasons and inputs clients. Root13 new CPU tests and retained11 native pairs
pass. Six actual900p physical archives contain871 retained intervals; matched
near/deep/tilt mean FPS improves11.66/13.57/16.69% in one sequential old/new pair.
Fresh ZIP authorization/hash cost is unchanged in policy but grows with the
embedded archive, so this is not isolated GPU causality, a universal speedup,
60FPS acceptance or normal-pack timing. Actual linked geometry hashes match.

Independent saved-reader replay and root reruns verify512 selected old/new
binary32 components exactly equal. Reasons preserve12/16 application and all
768 certificate calls (502 absent/266 supported/0 unknown); inputs retain four
supported category3 first targets, not all48 raw inputs/TES/application proof.
Unknown natural branch and simultaneous-draw evidence stay unavailable. Root
inspects all six stills; near/tilt PNGs byte-match, deep has particle differences.
Fine broken bands and polygonal rim remain, not fixed or physically accepted.
Next is the separately instrumented one-variable pre-Cholesky GH lattice-phase
diagnosis, not tolerance/blur/gate removal or automatic shipping promotion.

All TEST entry points are disabled; original configs and normal0.6/physics0.2
restored, ordinary save comparison matched before reopening without restoration
of a backup. Actual normal ordinary client is freshly inspected paused21:55:02,
with no later native GL. Shipping, motion, shore/cloud/transport/energy and the
FULL realism goal remain active and unachieved.

## Same-model conditional sampler checkpoint, 2026-10-06 12:34 JST

The [conditional-sampling evidence](../reports/2026-10-06-water-conditioned-sampling/README.md)
adds orthogonal Gaussian proposal axes and analytic conditional support without
changing raw normal/view/covariance, source units or survivor-mass normalization.
CPU16x4096 means meet all four retained T/R coefficient gates; this is not a
statistical confidence/temporal or low-ray-count convergence proof.
NVIDIA standalone port3904 scalar comparisons meet predeclared node gates after
a genuine CDF-only correction (max transmitted z error5.23e-5 ->3.68e-6).
Old rejected maps are retained. Proposal x remains CPU-generated.

A real tilted-camera MAIN now sees actual underwater opaque reflected sources,
with matched depth/geometry/inputs and a positive green-only C4 control. Both
dense and64-proposal source paths execute; the64 path sees48 reflected hits and
16 explicitly counted misses. Its green response differs from the dense result
by about0.43%, not accepted as converged first-visible-object transport.
Ten source/Sun/rain/opaque/cave/Moon cases retain exact raw controls. The64-ray
finite estimator matches its CPU replay, while its diffuse transmission error
9.246e-5 exceeds the unchanged6.883e-6 dense-reference gate. The native one-TEST-
pixel257x257 timing median9.578ms is still costly; it is neither Minecraft FPS
nor full-frame cost. Native regression suite11 pairs passes on RTX3080Ti.

No new candidate installed or candidate Iris/motion/visual acceptance claimed.
Normal0.6/physics0.2 reopened and root inspected ordinary runtime12:34:13 and
pause12:34:37, exact ordinary lock FD154. Save identity matched before reopening
without restoration; configs/Mod assets and disabled TEST entrypoints retained.
No native GL after handoff. Full natural shore/cloud/volume/radiance/weather/
night/contact/motion/energy goal stays active. Next is efficient same-model
inverse-CDF/proposal convergence, actual source and cost qualification, then
guarded disposable-world Iris validation; not automatic promotion of this slice.

## Same-model fast inverse and probability-panel checkpoint, 2026-10-06

The [fast-inverse/probability Evidence](../reports/2026-10-06-water-fast-inverse/README.md)
implements an independently fitted selected inverse and per-support-panel
probability quadrature, without changing raw optics, known masses, source units
or gates. Actual original-MAIN diffuse transmission RED9.2433e-5 becomes
GREEN5.38855e-7; wide-opaque7.55059e-7 also meets its retained dense gate.
Ten source cases/920 raw comparisons and native11 retained pairs pass.
Separate same-session one-TEST-pixel ABBA qualifies inverse-only speedup2.868x,
and fast64/probability8 speedup1.157x; neither is Minecraft FPS/full-frame cost.
Constant-source CPU4-context T/R success does NOT qualify actual object-source
convergence: reflection order8 is0.707% above retained dense and order12 is6.70%
below it. Higher order worsens that response; first-visible/source boundaries,
critical/general inputs, practical full-frame cost, Iris/natural/temporal/energy
and the full shore/cloud/physical goal remain open. No candidate installed.

Fresh41-file save identity and normal configs/Mod set/TEST disablement pass
before ordinary relaunch, with no save restoration/ordinary-world automation.
Normal0.6/physics0.2 runtime is freshly inspected13:01:38 and paused13:02:13,
owned handle16740 / hostJava3202154 / exact ordinary lockFD154. No native GL
after handoff. All old seals/failures preserved; goal remains active/unachieved.

## Observed-source viewport-exit correction checkpoint, 2026-10-06

The [source-boundary Evidence](../reports/2026-10-06-water-source-boundary/README.md)
isolates a real original-MAIN SSR omission: a coarse offscreen endpoint skipped
an independently known observed-plane receiver. A passive per-node observer
retains all optical MRT/depth bits. A one-variable last-in-viewport-segment
correction recovers1/6 misses in128/288-node conditions, with all previous
positive sources/path values retained exactly and no new outside hits. The
qualified function is implemented in production; retained11 NVIDIA pairs pass.
Actual first-plane RED6 -> GREEN0 does not prove arbitrary first-object geometry.

Corrected few-node source integration still differs by about1% from a finite
96-order dense rule: convergence remains rejected, with no relaxed gate.
Affected ten-case MAIN sources are prepared but not executed at this checkpoint.
No candidate installation, new Iris visual/motion acceptance, Minecraft FPS or
physical-energy proof. Full natural shore/cloud/volume/radiance/weather/night/
contact/motion goal remains active and unachieved.

Fresh41-file save comparison passes before ordinary relaunch without restoring
any save. Normal0.6/physics0.2 is reopened and root inspected runtime13:24:07,
pause13:24:13 JST; owned handle54078 / hostJava3220839 / ordinary lockFD154.
Original options/benchmark bytes, Iris noncomment properties, assets and disabled
TEST entrypoints are qualified. No native GL after handoff; old seals preserved.

## Affected MAIN and dense-source refinement checkpoint, 2026-10-06

The [boundary-regression Evidence](../reports/2026-10-06-water-boundary-regression/README.md)
now executes the prepared corrected ten-case MAIN sources:920 raw comparisons
and both unchanged selected dense transmission gates pass. With only the dense
quadrature table varied, corrected reflection orders96/128/192 give
.07443220913 /.07440861315 /.07439509779, adjacent changes.031711%/.018167%.
Independent cross-order replay qualifies234 input/geometry/non-rule comparisons
and113 raw controls per order. Finite192 is not certified truth. Dense variation
alone appears insufficient to explain remaining~1% few-node source differences;
efficient observed-source/critical/general geometry qualification remains open.

No new candidate installed, modified-candidate Iris/appearance/motion acceptance,
FPS measurement or physical-energy proof. Full realism goal stays unachieved.
Fresh41-file ordinary save/config baseline matches before reopening without any
save restore or ordinary camera/time/terrain automation. Normal0.6/physics0.2
runtime root inspected13:33:41 and final pause13:34:04; owned handle87409 /
hostJava3229665 / namespace16 / exact ordinary lockFD151, TEST disabled.
No native GL after reopening. The previous801-file source-boundary seal is
preserved; current liveness always requires revalidation rather than this note.

## Known-source boundary partition and SSR precision RED, 2026-10-06

The [observed-plane checkpoint](../reports/2026-10-06-water-observed-plane/README.md)
implements a CPU-only quartic window/fade partition with unchanged raw Gaussian
optics, mass, facet offset and source units.288 saved-input nodes +10,537
independent geometry queries and3 tests pass;440 previous numeric fields replay
exactly. Selected low-order known-plane/fade unit-response gates pass, but this
different functional is not actual SSR, arbitrary world geometry, GLSL or Iris.

An actual original-MAIN path/Beer precision RED is separately retained: first
center-source unit error.00173661 exceeds unchanged.00018419 gate, from returned
1.11961317m vs independently observed first-plane1.09716375m. All97 saved hit
confidence values are1; path/refined-UV precision, not those confidence values,
is the next causal seam. Actual binary32 camera/depth reconstructs receiver
Z=-5.99981689453125, not nominal6m; initial audit mistake/failure remains saved.
No shader/candidate installation, native GL or real-view improvement claimed.

Normal0.6/physics0.2 is freshly reinspected paused13:45:18; live owned87409 /
Java3229665 / namespace16 / ordinary lockFD151, TEST disabled and configs/assets
qualified. No ordinary save restoration or camera/time/terrain automation.
Full appearance/transport/cloud/physical/energy/motion goal remains unachieved.

## Actual SSR precision correction and current-renderer Iris checkpoint, 2026-10-06

The [path-precision evidence](../reports/2026-10-06-water-path-precision/README.md)
fixes the qualified actual original-MAIN Beer/path RED by changing only SSR
hit-refinement bisections4->12. All85 unchanged center gates pass; node0 unit
error.00173661 becomes.00000402472. All97 hits/191 misses and10,246 exact raw
input/geometry/weight/coarse-bracket/unrelated-MRT comparisons remain qualified.
Maximum97-hit path error.04507645m becomes.000176032m with the same actual
binary32 depth/camera reference. The tested function is adopted identically in
production. Retained11 native pairs/behaviors and a qualified nonvacuous closed
black-FIRST/red-BACKGROUND negative pass on RTX3080Ti; no tolerance relaxation.

A NEW exact-current-source TEST candidate is now genuinely run in actual Iris
at2560x1440/render12/sim6:9 native PNGs,3478 raw intervals, no fallback, all
capture windows focused, measured underwater poses/heads and scripted boat
contact. The original strict reader passes. Observed mean FPS ranges28.66rain
to118.57night; coast50.89/day35.77/moving44.15/boat62.96. These short workloads
are neither a4/12-only causal comparison nor a strict60FPS release gate.
The candidate includes preexisting uncommitted renderer work, not the native
probability12 TEST observer; normal0.6 assets/defaults are not promoted.

Separate900p20s/480-frame full-window moving-view footage and3 inspected decoded
samples are retained. Recording overhead never affects preceding1440p results.
Root inspects all9 native images: the old nested rectangular sky overlay is not
visible, but rough Snell-window rims, strong cyan/serrated shore and directional
streaks remain. Dome curvature alone is physical, not proof of an error. Whole
motion/contact naturalness, practical/general source integration, arbitrary
geometry, full coherent Sun/Moon/cloud/volume/physical-energy goal remain open.

TEST client exits0; a fresh41-file ordinary save/config baseline stays exact
through TEST and before reopening without any save restoration/ordinary-world
automation. TEST JARs/marker are recoverably disabled; normal0.6/physics0.2
reopens on owned62875/Java3253171/namespace16/ordinary lockFD154. Root inspects
native runtime14:00:29 and paused handoff; final checkpoint has the exact pause
image. Original options/benchmark bytes, Iris noncomment properties/assets and
disabled9 TEST entrypoints pass. No native GL after reopening; old seals retained.
The full realism goal is active and unachieved, not redefined as this correction.

## Actual natural-coast receiver/proxy witness, 2026-10-06

The [coast-attribution evidence](../reports/2026-10-06-water-coast-attribution/README.md)
adds two focused actual1440p coast atlas runs,499 raw intervals and bounded live
FINAL RGBA32F sampler qualification. Eight spatially separated dark/bright pairs
all match refraction miss/confidence0 vs opaque hit/confidence1. All16 are known
water, vertex-unknown0 and SSRmiss=-1; Fresnel.0489–.1194. Knowledge and SSR
switches do not explain these selected interior bands. Receiver/proxy transport
is strongly correlated, not yet a proved solver/visibility defect or correct
first-object/water-membership path. Same-invocation exit/search witnesses plus
independent first-visible geometry are next; no appearance-only fallback change.

Diagnostic Iris parser RED->GREEN and early-frame allzero readback rejection are
retained. Exact source recovery passes; production renderer/dist are unchanged.
Observed warmed5s means49.91/50.09FPS are diagnostic snapshots, not production
cost/quality/motion acceptance. PNG/selected raw are different frames; native
compile-only, live typed-sampler roles and source-neutrality evidence remain
separate, without an asserted C0/depth GPU-equality or general physical proof.

All TEST clients exit0. Original configs/threeJARs and41 ordinary saved files
match the fresh baseline before normal reopening; no ordinary-world automation
or save restoration. TEST controls disabled recoverably. Fresh normal0.6/
physics0.2 runtime14:17:48 and pause14:18:31 are root-inspected: owned68513,
Java3268991, exact ordinary lockFD154, window62914567 DISPLAY=:1. Old seals
retained; no native GL after ordinary reopening. Full realism goal remains active.

## Actual coast search-stop and negative budget ablation, 2026-10-06

The [coast-stop evidence](../reports/2026-10-06-water-coast-stop/README.md) captures
the original refraction invocation's stop/search fields for the prior eight dark/
bright pairs. All dark points hit iteration8 residual failure; all bright points
succeed. Actual seven distinct32F sampler roles, known water masks and observer
state restoration qualify the bounded raw records. No second trace or additional
depth lookup; production source hashes are unchanged.

A NEW TEST-only upper search-budget9->32 ablation preserves every guard/tolerance
and underwater8. At iteration31 all eight misses remain misses and all eight
positive neighbors remain hits. Simply extending the budget does not recover
these receivers. Physical first-object correctness and exact live-state A/B are
not proved. Strong cyan/serrated bands remain in the root-inspected actual atlas.
This negative experiment is not shipped or treated as visual acceptance.

Two focused2560x1440 coast runs retain483 positive raw intervals, mean49.647/
47.097FPS, P99 23.583/23.874ms; diagnostic atlas costs, not production timing or
a strict60FPS gate. Same-invocation raw fields do not imply PNG/raw simultaneity.
The exact guarded TEST coast region is retained read-only after clean exit for
independent world-space first-hit/source-visibility qualification before a fix.

TEST exits0; original configs/normal threeJARs and41 ordinary saved files exactly
match the fresh baseline before reopening, with no save restore/world automation.
Normal0.6/physics0.2 reopens owned34546/hostJava3281771; fresh runtime14:30:55 and
pause14:31:42 are root-inspected, all nineTEST entrypoints disabled. No native GL
after ordinary reopening; old seals preserved. Full natural water, motion/contact,
coherent Sun/Moon/cloud/volume and useful physical effects goal remains active.

## Actual world receiver/camera occlusion checkpoint, 2026-10-06

The [coast-world evidence](../reports/2026-10-06-water-coast-world/README.md) records
16 actual original-MAIN world rays and independent saved Anvil first-cube/camera
traversals. All eight dark physical first-sand receivers are camera-occluded by
a different nearer sand cube (0.6516–3.2609m before target); all eight adjacent
bright controls are camera-visible. Traversed states agree across closed saved
snapshots. This is bounded point-center/full-cube evidence, not finite source
pixel footprints, arbitrary geometry, frame-frozen state or solved appearance.
Production source hashes are unchanged; actual atlas remains cyan/serrated.

The [chosen next implementation](reviews/codex-occluded-water-receiver-next.md)
introduces conservative world geometry/material/light receiver support through
the read-only bridge, preceded by a genuine occluded-first-receiver production
regression. Smooth bathymetry is not occupancy/albedo/radiance. Do not force
screen-space hits, weaken guards or merely recolor an incorrect proxy path.

Actual focused1440p coast248 intervals:49.798FPS mean/P99 23.163ms, no fallback;
diagnostic atlas workload, not production cost or strict60FPS guarantee. Native
compile-only, actual Iris roles, world geometry and visual acceptance stay
distinct. Initial UI closure/owned-launcher143 and helper import misrouting are
retained failures; normal recovery18279 genuinely exits0/all dimensions saved
before new41-file baseline. No old sealed file was overwritten or save restored.
TEST13904 exits0; original configs/JARs/saved41files match new baseline before
normal0.6/physics0.2 reopens owned59228/Java3294081. Runtime14:45:21 and pause
14:46:18 are root-inspected,9 TEST entrypoints disabled, no native GL after final
ordinary reopening. The full realism goal remains active and unachieved.

## Receiver geometry implementation checkpoint, 2026-10-06

The [receiver-contract evidence](../reports/2026-10-06-water-receiver-contract-v3/README.md)
introduces a bounded immutable geometry snapshot and first-opaque traversal,
plus an optional loaded-chunk-only adapter candidate. All16 actual-MAIN
refracted and16 independent camera rays agree with the saved-world first-object
oracle;512 separate closed-box slab controls pass (348 positive). Unknown,
unsupported, unloaded, inside-solid and ambiguous boundaries cannot promote a
farther bed. Existing bathymetry tests and adapter/core javac pass.

This is **CPU geometry evidence only**, not the pending occluded-floor production
MAIN regression, actual vanilla appearance/radiance, live reflection/Iris sampler
binding, renderer integration or Minecraft visual/timing acceptance. No new
shader source, installed Mod, runtime config or world was changed. Ordinary
owned59228/Java3294081 remains live with0.6/physics0.2, lockFD153 and all9 checked
opt-in entrypoints absent. Old world/stop/handoff-addendum seals and the new19-file
contract seal verify. Continue the [recorded next action](../reports/2026-10-06-water-receiver-contract-v3/RESUME.md)
without treating geometry-only progress as full realism completion.

## Qualified original-MAIN occluded-source REDs, 2026-10-06

The [occluded-MAIN regression](../reports/2026-10-06-water-occluded-main/README.md)
runs the original water VS/FS with common public flat-wave/foam-off settings on
RTX3080Ti/GL4.6, independent closed cubes/source/depth and fixed pixels. Actual
passive original-invocation readbacks have zero C0 observer difference; independent
Snell/first-object/Fresnel/Beer and nine-point hidden footprint audits qualify them.
The hidden first-floor source response is0 rather than expected0.05931365; the
visible positive0.02627601 fits expected0.02615227 within2%. A second distinct RED
shows farther tagged radiance changing a known near-first pixel by0.09272926.
World/screen joining must therefore qualify miss-proxy source identity as well
as supply camera-hidden material. Neither behavior is fixed or shipped.

Synthetic native source fields are not real vanilla model/atlas/tint/light data,
Iris binding, nonzero-wave/tessellation or Minecraft visual/timing acceptance.
Boundary-point preparation, old-binary build race and result-classification
failures are retained; authoritative v4 uses a unique synchronously built binary.
No production shader/config/installed-Mod changes this turn. Clean ordinary
exit0 and a fresh41-file baseline precede native GL; baseline bytes remain exact
before normal0.6/physics0.2 reopens owned41749/Java3317128, lockFD154. Runtime
15:11:27 and pause15:11:33 are root-inspected; cyan/serrated appearance remains.
New375-file and prior19-file seals verify, no native GL after final ordinary
relaunch. Continue actual material/source bridge implementation per the
[next action](../reports/2026-10-06-water-occluded-main/RESUME.md); full goal active.

## Actual vanilla face-input bridge checkpoint, 2026-10-06

The [actual-face evidence](../reports/2026-10-06-water-receiver-faces/README.md)
implements a conservative immutable full-face UV/color/tint/raw-light decoder
and loaded-only pinned adapter. A standalone exact-world TEST observer captures
all16 former saved first-sand requests (14 unique cell-faces, UP/EAST/WEST) in
real MC1.21.1/Iris1.8.8 on NVIDIA RTX3080Ti/GL3.2. The original shader and
normal physics0.2 are unchanged; actual model rendering seeds/UV orientations
and raw adjacent sky8..12/block0 values replace registry-name guesses.

This is actual face-input evidence, not actual texture pixels, shaded radiance,
source upload/sampler readiness or solved water bands. Frame1 does not prove
light warmup, temporal stability, atlas epoch or saved/live-fragment coherence.
Brightness1.0 is the actual Iris/Sodium-context MC render-view return, not a
physical irradiance model or unmodified vanilla-face-shading proof. The two
qualified native-v4 REDs and cyan/serrated actual appearance persist. Focused
behavioral RED->GREEN record-audit/decoder checks and affected CPU regressions
pass; none substitutes for original-MAIN/Iris source and visual acceptance.

Old ordinary owned41749 and TEST owned28525 genuinely exit0 after clean saves.
The standalone probe and its properties are disabled recoverably. Original
configs/three Mods/41 ordinary saved files exactly match the fresh baseline
before normal0.6/physics0.2 reopening owned92351/Java3335948, ordinary lockFD154.
Fresh ordinary runtime/pause are root-inspected; all10 checked TEST entrypoints
absent. No native GL after normal relaunch, no new timing benchmark, old seals
preserved. Continue the [texture/source next action](../reports/2026-10-06-water-receiver-faces/RESUME.md);
the complete natural water/light/physical-effects goal remains active/unachieved.

The [face-handoff addendum](../reports/2026-10-06-water-receiver-faces-handoff-addendum/README.md)
corrects the preceding packet's invalid final-pause assertion: its15:34:03
candidate was gameplay and the recorder accepted a historical pause event.
The immutable45-file packet remains retained, with its actual16-face evidence
and before-reopening exactness valid. A genuine chronology RED->GREEN now
rejects that old handoff; actual root-inspected15:35:48 gameplay and15:36:17
game menu plus a fresh intervening normal pause event qualify the corrected
handoff of the same live Java3335948/owned92351/ordinaryFD154. No saves restored,
no world commands, no new native GL or source/rendering completion claim.

## Actual CPU receiver texels, 2026-10-06

The [static-texture checkpoint](../reports/2026-10-06-water-receiver-texture/README.md)
adds immutable actual sprite pixels, affine face sampling and loaded-only pinned
extraction. Three warmed real MC/Iris/NVIDIA observations yield48 face records/
240 sample checks, matching independent ImageIO stock-sand decoding and actual
known NativeImage channel/ownership controls. Eight requested first receivers
were camera-hidden in the prior saved geometry. These three records agree;
there is no general epoch/scheduling, saved/live-fragment or temporal proof.

This is CPU mip0 input, not GPU atlas filtering, smoothed light/AO or actual
shaded source radiance. Both original-MAIN native-v4 REDs and actual cyan/
serrated water appearance persist. No shader change, water fix, new timings,
motion acceptance or full-goal completion is claimed. Focused public CPU checks
and affected retained regressions pass. Clean TEST exit and exact41-file ordinary
baseline precede normal0.6/physics0.2 reopening owned8254/Java3363600; actual
15:57:08 gameplay and15:57:46 fresh pause are inspected. Probe/10 opt-in controls
are absent; no native GL after normal relaunch. OpenAL device initialization
fails in this launch, so the graphics checkpoint does not establish audio.
Continue exact first-face material ownership, actual GPU/lighting/source joining,
then unchanged original-MAIN and real natural/motion acceptance. Full goal active.

The subsequent [first-surface association](../reports/2026-10-06-water-receiver-surface-v2/README.md)
implements a bounded immutable CPU catalog and exact first-cell/block/normal
sampling. Six public-API RED->GREEN increments plus retained affected controls
qualify no farther borrowing, explicit caller-token staleness and capacity.
Sixteen original saved refracted rays now join their actual face/sparse texels
offline, without a new terrain/GPU run. This is not live frame/atlas coherence,
GPU filtering, shared lighting, original-MAIN source correction or natural
visual acceptance. Actual source production/GPU and lighting integration remains
the next implementation, with the full water/light/physics goal still active.

The [actual GPU atlas checkpoint](../reports/2026-10-06-water-receiver-atlas-v2/README.md)
now reads the already-registered block texture in real Iris/NVIDIA and verifies
48 whole-sprite/48 point matches against actual native CPU pixels and stock
decoding. Owned known GPU mutation/readback and listed state restoration pass.
The actual unsized RGBA format is accepted only after querying8-bit unsigned
normalized channels; the original rejected attempt/source remain preserved.
Raw mip0 and object filter metadata are not actual terrain-draw sampler/LOD,
atlas reload/geometry-frame coherence, shaded radiance or production source
binding. No shader correction, timing/motion acceptance or full goal completion.
Both native-v4 REDs and cyan/serrated water remain. Normal0.6/physics0.2 is restored
after clean TEST exits, with exact41-file ordinary state before reopening
owned79690/Java3386746. Continue actual coherent material/lighting source joining.

## First world-source MAIN candidate checkpoint, 2026-10-06

The [first-source packet](../reports/2026-10-06-water-receiver-main/README.md)
now adds an optional bounded geometry/source shader path, correcting the two
unchanged native-v4 synthetic fixture failures: hidden-first green response
0.05931365 matches the independent Fresnel/Beer value, and near-first farther
color borrowing becomes zero. Whole fixture inputs/oracle/observer are unchanged,
actual shader first paths agree and observation C0 difference is zero. Additional
unready-first RED->GREEN preserves known first geometry without borrowing a
farther source. With readiness zero, four full C0 and seven observed fields
match the original exactly. Retained actual NVIDIA `make check` (11 pairs),
absolute direct radiance and nonzero-wave first-visible-bed gates pass.

The source is still synthetic homogeneous-voxel air-lit radiance, not real
per-face material/filtered atlas/light/AO or a live coherent Iris producer. The
new positive world-source Sun branch and water-volume/stale input gates need
their own qualification before source promotion. Installed normal0.6/physics0.2
are unchanged. No new natural appearance, frame timing or motion acceptance is
claimed; cyan/serrated shoreline and full coherent water/light/physics goal remain
unachieved. Continue exact source/Sun joining and real-world validation from
the packet's RESUME.md; never substitute a native synthetic pass for that goal.

## Positive first-source Sun / vertex-input checkpoint, 2026-10-06

The [Sun/input packet](../reports/2026-10-06-water-receiver-sun/README.md)
qualifies the formerly pending positive world-source Sun branch on an unchanged
flat synthetic MAIN fixture: actual red0.00168775022 matches independent optical
energy0.00168774753, with zero other-channel and passive-observer changes. Four
missing/invalid paired-Sun controls reject material promotion. An immutable
pre-encoder vertex module now preserves actual-input tint/AO/light conventions;
four genuine CPU RED->GREEN increments and pinned installed bytecode qualify
that preparation, not actual game mesh capture or shaded radiance.

Actual mesher/encoder events, per-face filtered material/shared lighting,
coherent live geometry/resource epochs, partial-water/displaced interfaces and
dynamic Iris source binding remain required. No production shader/installed
normal0.6 or physics0.2 changed; no natural shoreline/motion/new frame timings
or full-goal acceptance is claimed. Ordinary gameplay and subsequent fresh pause
are inspected at16:58:25/16:58:49; checkpoint records the live owned handoff and
all disabled TEST opt-ins. OpenAL device initialization still fails. Continue
the new packet's RESUME.md; full realistic water/light/physics goal stays active.

## Actual mesh-source inputs, 2026-10-06

The [actual mesher/encoder packet](../reports/2026-10-06-water-receiver-mesher/README.md)
now captures14 exact requested first-sand faces/56 vertices from two actual
Sodium worker threads in UUID-guarded V2, and independently matches280 initialized
Iris encoder words. Owner coordinates, actual tint/color, AO0.39996338..1 and
smoothed raw sky bytes128..192 are immutable, not neighboring-light/AO guesses.
No vertex/native buffer/terrain writes or ordinary world commands occur.

Actual terrain draw decode/interpolation/matrices/filtering, coherent mesh/atlas
epoch, real per-face shared illumination/Sun source and dynamic Iris binding
remain required. No new shader, normal release, frame timings or motion-quality
acceptance is claimed. The inspected unchanged TEST image still has cyan water
and serrated shore bands. Clean TEST exit and byte-exact ordinary state before
reopening precede safe normal0.6/physics0.2 handoff in its checkpoint. Continue
its RESUME.md toward original-renderer natural acceptance; the full goal remains
active, not achieved by this actual-input milestone.

## Actual draw-input / vertex decoder checkpoint, 2026-10-06

The [actual draw packet](../reports/2026-10-06-water-receiver-draw/README.md)
now records the bound original terrain VAO, actual linked Iris sources, lightmap
matrix, atlas UV shrink and effective sampler metadata. An owned VS-only NVIDIA
fixture uses the unchanged linked source and archived actual56 vertices; all448
UV/lightmap/color floats match both the immutable CPU decoder and independent
scalar audit with zero float32 error. Iris takes raw light bytes into the observed
1/256-scale,1/32-offset matrix; generic Sodium pre-division would be incorrect.
Original terrain multi-draw returns and the listed original GL state is restored.

This is not actual original-face fragment shading, filtered atlas fetch, live
mesh/resource coherence, paired per-face source radiance, or dynamic Iris source
binding. No shader/normal0.6/physics0.2 change, new Minecraft frame timings or
visual/motion acceptance is claimed. The inspected TEST view remains cyan and
serrated. Ordinary state is restored byte-exact before reopening, with no save
rollback or world commands. The packet checkpoint records subsequent normal
runtime/pause verification and remaining audio initialization limitation.
Continue per-face actual shading/source integration rather than promoting a
homogeneous voxel approximation; the full realistic water/light/physics goal
remains active and unachieved.

## Per-face triangle interpolation checkpoint, 2026-10-06

The [triangle packet](../reports/2026-10-06-water-receiver-triangle/README.md)
implements immutable piecewise-linear attributes at the first actual face, using
the installed Sodium generator's exact0-1-2 /2-3-0 pattern and archived mesher
order. Its full-unit boundary rejects unknown/degenerate inputs rather than
guessing farther material or AO. The unchanged actual Iris VS is qualified in a
standalone NVIDIA GL4.6 pass-through fragment fixture at16 saved first-hit points
and42 supplemental points, with orthographic and projective transforms. All928
positive interpolants match independent evaluation within8.731773e-7; a wrong
diagonal control changes attributes by0.10196084. Three genuine public API
RED->GREENs and copied evidence-negative controls are retained.

This proves bounded attribute interpolation, not original live index binding,
filtered atlas fetch, shared-light/Sun radiance, coherent live resource epochs or
actual source upload. No production GLSL or normal0.6/physics0.2 changes; no new
Minecraft timings, natural shoreline or temporal acceptance is claimed. The
ordinary world is cleanly saved before native testing, fresh41-file/config/Mod
state stays exact before reopening, and checkpoint records the subsequent normal
runtime/pause. Continue actual filtered material/shared original illumination and
renderer binding from RESUME.md. Full water/light/physics goal remains active.

## Actual filtered material / lighting resources, 2026-10-08

The [resource/material packet](../reports/2026-10-06-water-receiver-light/README.md)
captures16 active original-terrain uniforms, actual atlas mip levels, cached
lighting LUT and shadow pixels in real Iris/NVIDIA GL3.2. Eighty controlled
`textureGrad` queries of the actually bound atlas agree with an independent raw
mip/filter oracle within7.620236e-6; copied misleading capture controls reject.
This adds actual fetched material to the preceding vertex/triangle qualification,
not original receiver shading or a newly accepted natural-water visual correction.

Geometry is archived, so coherent live ownership/epochs and natural fragment
derivatives remain unproven. Shared original terrainLight/paired Sun source,
dynamic Iris binding, partial/displaced interfaces and natural motion/weather/
contacts/full lighting acceptance remain required. Missing source readiness is
not promoted. No production shader/normal release changed or new frame timings
were measured. The packet preserves failed build/runtime evidence and an unknown
interrupted v2 exit; its new v3 TEST exits0, ordinary state is exact before reopening,
all13 opt-ins are removed, and a fresh normal0.6/physics0.2 handoff is recorded.
The full original realistic water/light/physics goal remains active, not achieved.
