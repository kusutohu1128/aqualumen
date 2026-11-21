# 陸上影プレビュー

水の開発は保留し、通常版0.6を土台に陸上の影だけを変更しました。比較するテクセルごとに受光面の深度を求め、4点の比較結果を補間します。通常版の水、雲、影マップ生成とグローバルなサンプラー設定は変更していません。

[プレビューZIP](Aqualumen-LandShadows-Preview-2026-10-23.zip)のSHA256は`ea3cbd1e19453aabc1807df7016549001379714a47e57187b3b72a31be0e6652`です。Labにも同じZIPを追加済みですが、現在は選択していません。通常選択は0.6、physicsは0.2、Labは終了状態です。

## 確認できたこと

RTX3080Ti、NVIDIA580.173.02の制御された描画テストで、4cmの隙間の光漏れと、光軸から離れた60度斜面の自己影を再現してから修正しました。両ケースの誤判定はそれぞれ16641画素から0画素になり、全26ケースが合格しました。これは特定の合成形状での結果で、任意の自然地形の改善率ではありません。

固定した影の縁を0.2mにわたり513位置で評価したテストも合格しました。最大の可視率変化は0.0091095で、事前に定めた0.02以下でした。これは固定光源に対する受光面移動であり、動く太陽の安定性やFPSの測定ではありません。

| 検証 | 結果と根拠 |
| --- | --- |
| pack境界とCPU | [28テスト](candidate2-checks/unit.stderr)が成功。元の46項目のうち2行だけを切替え、44項目と23本の非不透明プログラム展開を保存。 |
| 実GPUでのコンパイル | [11描画ペアと3compute](candidate2-checks/compile-only.stdout)のコンパイル・リンク成功。実行テストとは別。 |
| 実影描画による形状判定 | [旧方式](native-baseline1/capture/RESULT.json)で失敗を再現し、[候補](native-candidate2/capture/RESULT.json)の全26ケースで誤判定0。 |
| 固定光源の移動テスト | [513位置](motion2-checks/land/RESULT.json)で端点コントラスト、単調性、最大変化量が合格。 |
| 故意に壊した対照 | [3種類](negative-controls1/receipt.json)で平面深度の未補正、過大バイアス、補間なしを検出。 |
| 実Minecraft | [通常版](runtime1/ordinary-run/run.json)と[候補](runtime1/candidate-run/run.json)で各3場面を完了。1600×900、Iris1.8.8、Minecraft1.21.1、RTX3080Ti、正しいZIPの有効化とfallbackなしを確認。 |
| 復帰 | [記録](runtime1/restored.json)と[独立した現物確認](VISUAL-RESTORE-REVIEW.md)で設定・mods・instance.cfg・通常ワールド全41ファイルのSHA一致、TEST無効化を確認。通常ワールドは開かず、巻き戻していません。 |

## 実ゲームの画像

[逆光の壁](runtime1/candidate-run/air-shadow-backlit.png)、[順光の壁](runtime1/candidate-run/air-sunlit-front.png)、[壁なし対照](runtime1/candidate-run/air-backlit-open.png)を保存しました。旧版との全6枚を親Codexと独立レビュアーが確認しました。閉じた壁は標的と光源を隠し、開放対照では標的が見え、候補だけの明確な描画破損は見つかりませんでした。

この浮遊壁の3場面は互換性確認です。自然な接地影や地形の自己影の改善を画像だけで直接立証する場面ではありません。雲・水・露出は時間変化するので、RGB差から画質向上とは判断しません。水のソース保存も、水面への映り込みの完全一致を意味しません。

## 判断と残る範囲

Model the DomainでREFUSED・LEGACY・METRICの受光面状態を分けました。Boundary Disciplineで投影と実機状態を検証し、不正な入力を物理的な可視性の証拠としません。Fix Root Causesでテクセル中心と受光面深度の不一致を直し、補正量を拡大して合格させる方法は採用していません。

Separate Before Serializing Shared Stateで水の未公開差分と通常環境を隔離しました。Exhaust the Design SpaceでClaude・Codexの案を比較し、Laziness Protocolで新規サンプラーやcaster変更を避けました。Build the LeverとTest Behavior Not Implementationで再実行できるpack生成・実影描画・故障対照を残し、Prove It Worksで実Irisと復帰後の現物まで確認しました。Explain the Numberに従い、[他プロセス負荷下の短時間撮影](MEASUREMENT-INTENT.md)から性能改善は主張しません。

元の法線方向offsetは保持し、2mmは追加の光軸方向深度補正です。総ずらし量が2mmではありません。標準8tapの各tapで最大4回の比較取得が必要になり、実コストは未測定です。接触硬化、太陽の物理的な半影、GIの実装ではありません。

自然地形の接地場面、動画、動く太陽と月、極端な角度、投影の広い組合せ、境界の時間的安定性、1440p性能は未承認です。新しいnative証拠は一つの固定した光源行列に限定します。[次の確認事項](OPEN-ISSUES.md)を残しています。

実際のClaude Opusは[設計](claude-design/RESULT.md)と[案の比較](claude-crossjudge/RESULT.md)を担当しました。最終コードレビューは[利用上限の429](claude-review/response.json)で未取得です。[独立Codexレビュー](CODEX-FINAL-REVIEW.md)と実機確認をClaudeの最終レビューとは数えません。通常版への採用、公開、完全な共同レビュー完了は保留です。

## 再生成

rootの通常buildは水関連の開発差分も含むため、このプレビューには使いません。保存した通常版を基に生成します。出力ZIPとmanifestが存在すると上書きを拒否します。

```bash
rtk proxy python3 tools/land_shadow_pack.py \
  --base reports/2026-10-23-land-shadows/ordinary-0.6.zip \
  --output /tmp/Aqualumen-LandShadows-Rebuilt.zip
rtk proxy python3 -m unittest discover -s tools -p test_land_shadow_pack.py
```

深度補正の考え方は[MicrosoftのPCF受光面深度資料](https://learn.microsoft.com/en-us/windows/desktop/DxTechArts/cascaded-shadow-maps#calculating-a-per-texel-depth-bias-with-ddx-and-ddy-for-large-pcfs)、サンプラーの契約は[Khronosの比較モード資料](https://wikis.khronos.org/opengl/Sampler_Object#Comparison_mode)を参考にしています。既存パックのソースはコピーしていません。
