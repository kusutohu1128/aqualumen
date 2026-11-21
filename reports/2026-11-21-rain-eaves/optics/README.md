# 雨膜（wet dielectric film）光学のGPU独立検証

対象: `release/shaders/lib/dielectric_film.glsl`（`filmDirectBRDF` / `wetSubstrate`）、`lib/rain_material.glsl`（`rainMaterial`）、
`lib/local_lighting.glsl` の 9 引数 `lampLighting(..., bool film, out vec3 reflectedLamp)`。
実行: `make check-film`（= `build/glcheck release/shaders --rain-film-probe`）。プローブ本体は `tools/rain-film-probe.h`。
レンダラ: **NVIDIA GeForce RTX 3080 Ti/PCIe/SSE2, GL 4.6.0 NVIDIA 580.173.02**（ソフトウェア描画ではない。ログ冒頭に必ず出力し、llvmpipe 等なら警告する）。

## 結果（親の実ファイルに対して）

| 項目 | 結果 |
|---|---|
| `gpu-film-final.log` / `.json` | **51,793 checks, 0 failed, 0 pending**（21 グループ） |
| `gpu-film-make-check.log` | `make check-film` 同結果、exit 0 |
| 負の対照 `mutants-2026-11-21.json` | 親の実GLSLを1箇所ずつ壊した **23/23 を検出**（全件、実テスト失敗由来。コンパイルエラー由来ではない） |
| 独立クロスチェック `albedo-crosscheck.txt` | 純Python格子積分とGPUアルベドが最大 0.52 %（格子解像度律速）で一致 |
| 旧パック回帰 `gpu-play-release-old1.6.0.log` | `dist/Aqualumen-1.6.0.zip` を `--play-release`: film 無しは `INFO ... no film probe` でスキップ、exit 0 |
| 現行 release の `--play-release` | フック経由で film プローブ実行を確認（`gpu-play-release-current-entity-fixed.log`）。ただし下記の既存バグのため **修正なしの `make check` はまだ落ちる** |

## 何を検証したか（何が独立か）

オラクルは倍精度CPUでの教科書式（GGX + Smith + Schlick, F0 = 0.0204 を half vector で評価）と Kubelka-Munk の式で、シェーダ定数のコピーではない。

- **BRDF**: 24,000 の乱数 (n,v,l,roughness,extent)（任意座標系、半数は鏡面ローブ内サンプル）でCPUと照合。最悪相対誤差 0.25 %。
  マスキングは **height-correlated Smith** と同定（separable Smith とは 12,809/24,000 点で食い違うので判別力がある）。
  正値・有限性、半球外（l/v が下半球）で厳密に 0、相反性（最悪 2.4e-5）、座標系回転不変（最悪 2e-3）。
- **F0 と幅の再現**: 法線入射 f = F0/(4·a²)、a² = roughness⁴ + emitterSlope2 が 48 通りで 3e-5 まで一致（幅の式そのものを逆算で確認）。
- **正規化/エネルギー**: 方向アルベド（半ベクトル層化求積。求積自体を Lambertian=1 と立体角ブルートフォース格子で対照済み）がCPUと 1e-5 で一致。
  全 48 ケース（視角6×粗さ4×extent2）で ≤ 1。法線視でアルベド ≈ 0.0204（= F0 を再現）、掠め視で上昇（89° で 0.49）。
- **粗さ/広がり/角度応答**: 鏡面ピークは粗さ・emitter 広がりで単調減少、軸外応答は粗さで増加、面内スイープのピーク位置と FWHM がオラクルと一致。
  ピークは鏡面方向〜掠め側 1〜3° にずれる（Fresnel と遮蔽による既知のoff-specular。独立Pythonでも同じ）。
- **数値端**: r=0、巨大/微小 extent、水平線上、反平行（半ベクトル長0）などすべて有限・非負。
- **wetSubstrate**: KMオラクルと最大 2.3e-7。ratio=1 で恒等（2.4e-8）、黒→黒、白→白（全 ratio）、ratio に対し単調（湿るほど暗い）、乾燥反射率に対し単調、`wet ≤ dry`、チャネル独立、範囲外入力でも有限。
- **rainMaterial**: id 0..12000 + 範囲外 id を全走査。適格は 9 id / 6 種のトリプル、全て block.properties に登録済み。非適格は被覆 0 かつ ratio = 1。
- **ランプ経路（実際の置かれた光源）**: 本物の `shadow_*.vsh` キャプチャ + `shadowcomp1.csh` 発行後に実 `lampLighting` を駆動。
  ランプのエネルギー定数に依らない比検定: `reflectedLamp == diffuse × filmDirectBRDF(n,v,l,roughness, r²/(4·max(d²,0.1)))`（288 受光点、最悪 6e-5）。
  旧 7/6 引数オーバーロードは bit 同一、`film=false` は反射 0、拡散戻り値は film に非依存。遮蔽壁は拡散・湿潤反射を同時に消し、半影でも BRDF 比が保たれる。
  暖色/ソウル松明で反射色が光源色、2灯の線形加算、視線方位に対するピークが幾何鏡面（±0.25°内）、鏡面/40°外し比 2.7e5、グリッド端 24 m のフェードを拡散と共有、24 m 超で 0、
  背面・下向き・消灯・光源なしで 0、vanilla 残差が湿潤反射を生まない、本番の水面スペキュラと 1e-7 で一致（「1x spec」を共有）。

## 範囲の限定（主張しないこと）

直接入射の微小面反射（粗い基材の上の薄い濡れ膜）と、二流束の散乱低減による基材の暗化のみを検証した。**膜厚・膜内多重反射・屈折・サブサーフェス輸送などの参加媒質モデルは検証していない／主張しない。**
計測は正しさのオラクルでありベンチマークではない（時間はあえて記録していない）。Minecraft のフレーム時間ではない。

## 所見（親・他担当への報告）

1. **`make check` / `make check-entity` が現行 release で落ちる（私の変更とは無関係の既存バグ）**: `tools/entity-light-probe.h:313` が `const GLuint junk=0xA5A5A5A5u;` を `glClearTexImage(..., nodes.format /*RGBA整数*/, GL_UNSIGNED_INT, &junk)` に渡し、
   ドライバが 4 バイトの変数から 16 バイト読む（スタック over-read、UB）。1.6.0 パックでは偶然無害、現行 release では glibc の malloc assert / SIGSEGV（`gpu-play-release-current.log`、
   `--entity-light-probe` 単体でも再現）。ASan の最初の報告も同一行。`junk` を `GLuint[4]` にする1行修正で全通過（差分: `entity-light-probe-junk-fix.patch`。**私はリポジトリを変更していない**、/tmp のコピーで検証）。
2. 単散乱GGXのエネルギー損失: r=1 では法線視アルベドが 0.31·F0（独立Pythonでも一致）。`rainMaterial` の最大 roughness は 0.52 なので現状は影響しないが、粗さを上げるなら多重散乱補償が必要。
3. `lampLighting` の湿潤項は `AQUALUMEN_HAND` / `AQUALUMEN_DYNAMIC_MESH` ビルドの手持ち光ロールオフ（拡散のみに適用）を受けない。film=true を手/メッシュで使うならホットスポットに注意（このプローブは両定義なしの地形経路を検証）。
4. グリッド端フェード（19–24 m）は拡散と同一係数で湿潤項にも掛かることを確認済み。

## 運用メモ

- レンダーロック `/tmp/aql-render21-1000.lock` は他エージェントのスクリーンショット撮影が保持し続け、待ち行列が出来ていた。本検証は約 11 秒のヘッドレス EGL テストで、指示どおり撮影を待たずに実行した
  （負の対照では各回の開始時にロックが塞がっていたかを `render_lock_busy_at_start` に記録：23/23 で true）。ゲーム・Lab・既存証跡には触れていない。
- 負の対照: `film_mock.py`（変異の定義、実ファイルはコピーに対してのみ適用）、`run_mutants.py`（実行）。`python3 -I film_mock.py list` で23件の一覧。
- 再現: `sources.sha256` に検証時のシェーダ/プローブ/バイナリのハッシュ。`AQUALUMEN_FILM_JSON=<新規ファイル>` で機械可読結果（既存ファイルは上書き拒否）。
- 開発ログ `gpu-film-dev1.log`: 最初の実行で 10 件失敗したが、全て私のプローブ側の仮定の誤り（鏡面ピークは掠め側へずれる、尾部はグレージングで単調でない、粗さ0.6での FWHM は粗さの尺度でない、遮蔽壁が広すぎて非遮蔽点がない）で、
  独立Pythonで物理的に正しいことを確認してオラクル側を直した（親のコードは変更不要だった）。`dev2` 以降 0 失敗。
