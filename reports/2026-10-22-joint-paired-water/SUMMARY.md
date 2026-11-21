# 共同開発の到達点

2026-10-22。水中の表示画像と反射分類を、実際の同じFINAL描画呼び出しから取得する診断機能を実装・検証した。水面の輪郭の巻き込みは取得画像にも残っており、見た目の修正完了ではない。

## 分担と実装

実Claude CodeのOpusが設計と生成器・テストを提案し、親がパッチを確認・適用した。別のCodex作業者が独立した観測ModとGPU試験を実装した。書き込み先を分離し、最終統合とLab実行は親が担当した。Claudeの別セッションが統合レビューを実施した。元のシェーダー、旧Evidence、通常配布ZIPは変更していない。

Model the Domain原則に従い、同一呼び出しの識別情報・要求・復元対象を明示的な型にした。Prove It Works原則に従い、コンパイルだけでなく実NVIDIA描画と実Irisの読出しを確認した。

MRTのC12に実際に使われた反射経路・Fresnel・距離・水面マスクを保存する。追加のレイトレースは行わない。FINALの実samplerが指すC12をquad直前に、実クライアントFBOの画像を同じquad直後に読む。preview=0、program/frame/renderer/pipeline/targets/viewport/camera/samplers、GL読出し状態の復元を検証した。画像と分類は1600×900。

このTESTでは波の評価時刻だけ17秒に固定し、接触波のサンプリングを無効化した。雲・その他の時刻とシミュレーション自体は停止していない。物理Modは実験用v100。通常0.6/physics0.2の見た目・性能を測ったものではない。

## 観測結果

| 上向き視点 | ワールド反射取得 | 既知だが光源未準備 | 未対応・不明 | 生成停止 |
|---|---:|---:|---:|---:|
| 水面下約0.5m、frame88 | 47.60% | 10.53% | 41.87% | 0% |
| 水面下約3.25m、frame201 | 52.87% | 8.15% | 38.99% | 0% |

分類上の画面内反射SSRは両フレームとも0画素。ただしSSR1の制御GPU試験は未実施で、SSRが実際に存在しなかったとは断定しない。非有限SSR結果がUNKNOWNへ分類される仕様もある。生成停止だけで全画面を説明する仮説に合わないという判断は、このSSR件数ではなく、肯定試験済みの取得済み経路とlighting-captured/source-ready=2ログの組合せに基づく推論であり、producer資源の直接同定は未実施。これらは元の水面画素の反射経路であり、最終色の原因比率ではない。FINALの近傍混合、GL_LINEAR、屈折光、後続の半透明描画も寄与する。経路別の平均輝度だけで不具合の原因は断定しない。

近接視点の表示座標(1430,200)は中心と隣接4画素とも取得済みワールド反射で、Fresnelは約0.36。深い視点の同座標も取得済みで約0.077。巻き込み全体を反射未対応だけに帰属させず、次は同じ入力の界面形状・光学法線・屈折方向を対応させる試験が必要。

## 検証と記録

- CPUは生成器18件と復旧5件、計23件成功。観測ModのJavaテスト53 assertions成功。
- RTX3080Tiで両生成物の14描画program pairと3computeをコンパイル・リンク。実描画試験は別記録。
- Nativeの6ケースでC0の全画素がバイト一致。route0/2/3/4/5、半透明非水面の分類消去、不正route9検出を確認。SSR1の制御試験は未実施。
- 実FINAL shaderでもpreview0のRGBA8全画素が一致。preview1は期待した分類パターンへ変わった。ただし実Minecraftではpreview1や非水面のblend消去を試していない。
- 実Minecraftは正しいpack SHA、NVIDIA、no fallback、V2 UUID/seed/単独プレイヤー/非LANのscopeを確認。近・深の両manifestで同一FINALと状態復元が成功。
- [AUDIT-final.json](AUDIT-final.json)はrawの有限値・分類件数・ファイルhashとPNG/rawの上下対応、native Evidence、元shader hash、通常設定復帰を監査し、入力manifestと主要Evidenceのpath/hashも記録した。旧AUDIT.json/v2は保存した。
- compileログだけでは入力packや終了状態を識別できない。[compile-provenance.json](compile-provenance.json)に当ターンの実行コマンド・返却終了コード・入力ZIPとの対応を後追いで記録した。同一内容の二つのcompileログだけを別入力の証明には使わない。
- [近接画像](runtime/underwater-up-near-paired-capture/beauty.png)と[深い位置の画像](runtime/underwater-up-deep-paired-capture/beauty.png)に見た目の残課題を保存した。

ClaudeレビューのM1は、nativeの生receiptと親のqualification.jsonを取り違えた指摘。実際の実行は両者をhashで結んだqualification.jsonを使用し、未試験SSR1も明示した。CLI説明と今後のbaselineへの未試験項目の記録を補った。M2の途中コピー復旧は妥当な指摘で、非jar一時名への書込み・hash確認・排他的公開と、一時ファイルを保持した復旧を追加した。バックアップも変更開始前に照合する。復旧修正は使い捨てファイルで検証した。完了済みMinecraft観測を、この復旧処理だけの変更のためには再実行していない。

[当時のruntime source](runtime-used-source-reconstructed.py)と[復元根拠/hash](runtime-source-provenance.json)を保存した。これは起動時に採取したhashではなく、Claudeの当時の完全Read記録と起動前4行のguard追加から後追い復元し、現在版から後日のstaging差分を除いた内容との一致も確認したもの。現在のCLOSURE.jsonが記録するsource群は、その作成時の状態であり、後からEvidence参照を追加したaudit scriptの最新版と同一とは主張しない。

コメント専用レビューは正しさの障害なし。GL_READ_BUFFERのFBO所有に関する説明は保持。生成済み試験ZIPのhashを変えるだけのコメント整形は本単位に含めず、残項目として保持した。コメント削除ゲートや公開承認を完了したとは扱わない。

## 安全な終了状態と次の単位

[restored.json](runtime/restored.json)の通り、通常Aqualumen0.6 / physics0.2、Mods・設定・instance.cfgを完全に復帰した。通常セーブは開始時とhash一致し、セーブの巻き戻しはしていない。TESTのMod/packは復旧用cacheへ移した。V2だけの試験履歴、観測raw、gamerule/time変更は残る。通常ワールドを起動していない。

未完了は、同一入力による屈折方向・法線・界面geometryの切り分け、SSR1の制御試験、実Irisの非水面blend消去、動く自然水面での見た目合格。植生の実反射と完全な流体物理も未完了。通常環境へのこの実験版の配布、commit、PRは行っていない。
