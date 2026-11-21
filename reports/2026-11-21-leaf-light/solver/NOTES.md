# Leaf light solver: 設計ノート

仕様の正本は `INTERFACE.md`。ここは判断の理由、参照文献、制限をまとめる。

## 1.7.0 で何が起きていたか
* 太陽: `direct *= max(dot(n,sun),0) * shadowVisibility(...)`。葉の可視面が太陽と反対側 (`n·sun<0`) だと 0。さらに、仮に余弦を外しても、シャドウマップの最初の面は立方体の反対面 (上面) なので、下面の受光点は常に影になる。
* ランプ: `if(nl<=0) continue;` で裏側の光源は捨てられる。葉の弦長減衰 (`shape==2`, `exp(-1.45 d)`) は、前面から見て葉の向こうにある光源の経路にだけ効いていた。
* 立方体の可視面の位置から読む格子セルは、面が整数平面上にあるため `floor(p)` が隣セルを引き得る。

## 設計判断
1. **所有セルは面から導く**。法線軸は 0.5 m 内側、接線軸は面内。`at_midBlock` や頂点属性を足さない (`TerrainRig` は `mc_Entity` のみ供給するため、親のプローブと同じ経路で動く)。起点はセルの 1 mm 内側へクランプするので、光路は必ず所有セルから始まる。
2. **シャドウマップは樹冠の外でしか使わない**。受光点自身や立方体の反対面を読むと自己遮蔽で葉の透過光が消える。近傍は格子 DDA で樹冠の上端 `tTop` を求め、その外側 (`+0.25 m`, `+1.5 m`) でのみシャドウマップを引く。これで、格子に無い屋根 (合成シャドウマップの平面、格子外) は止め、樹冠自身は止めない。
3. **丸太・屋根は格子で確実に止める**。`shape` 1/3/4/5/6-9 と角の同時横断は `lampTransmission` と同じ規則。近傍では葉と丸太を区別できる (格子はブロック ID から作られる)。
4. **隠れた内部セル**。外面しか描かれない塊の内部は未登録。葉の連続の中でだけ、6 方向すべてに K=4 m 以内で固体か葉があるセルを葉とみなす。画像は変更しない (ローカルライトの既存プローブがフィールドを bit 単位で照合するため)。
5. **反射と透過の分離**。`albedo` は前面の反射のまま。透過率は `τ = κ s ρ` (κ=0.6)。色相は実際のアトラス × 色味から決まる。`s` は明るい花弁で `ρ'+τ ≤ 1` を保つ共通スケール。
6. **光源ごとに独立**。太陽は 1 回のトレース、ランプは 1 つずつトレース。壁は 1 つの光源の経路だけを閉じる。
7. **洞窟では光らない**。透過項は実在の光源 (太陽・月・リスト内のランプ) の積だけ。太陽は 1.7.0 の直達日射と同じ `smoothstep(0,0.85,lightmap.y)` と雨の係数でゲート。
8. **遠方 (`c_g<1`)**: 格子が無いので、所有セルの出口の先 7 点のシャドウ判定から樹冠の厚さを期待値で推定し、近傍と 16–22 m でブレンドする。

## 参照文献 (一次資料。コードは参照していない)
* Gates, D. M., Keegan, H. J., Schleter, J. C., Weidner, V. R. (1965). Spectral properties of plants. *Applied Optics* 4(1), 11–20. 葉の反射率・透過率の分光。
* Jacquemoud, S., Baret, F. (1990). PROSPECT: a model of leaf optical properties spectra. *Remote Sensing of Environment* 34, 75–91.
* Verhoef, W. (1984). Light scattering by leaf layers with application to canopy reflectance modeling: the SAIL model. *Remote Sensing of Environment* 16, 125–141. 二面ランバート (反射・透過) の葉。
* Monsi, M., Saeki, T. (1953). Über den Lichtfaktor in den Pflanzengesellschaften und seine Bedeutung für die Stoffproduktion. *Japanese Journal of Botany* 14, 22–52. 樹冠内の Beer–Lambert 減衰。
* Nilson, T. (1971). A theoretical analysis of the frequency of gaps in plant stands. *Agricultural Meteorology* 8, 25–38. 葉の面積密度と隙間確率。
* Ross, J. (1981). *The Radiation Regime and Architecture of Plant Stands*. Dr W. Junk.
* Kubelka, P., Munk, F. (1931). Ein Beitrag zur Optik der Farbanstriche. *Zeitschrift für technische Physik* 12, 593–601. (検討したが採用せず。下記)
* Habel, R., Kusternig, A., Wimmer, M. (2007). Physically based real-time translucency for leaves. *Eurographics Symposium on Rendering*. 葉の透過を近似する際の背景。

KM 二流束は採らなかった: 与えられた `ρ∞` からの透過は `exp(-b s)` で急速にチャンネル間のコントラストが開き、緑以外が 0 に近づいて色相が不自然になる。可視域の τ/ρ が概ね 0.5–0.8 とされること (Gates ら。数値は記憶に基づく目安で、原典での再確認が必要) に合わせ、`τ = κ ρ` を選んだ。

## 既知の制限 (INTERFACE.md §7 と同期)
* L1 遠方では丸太と葉を区別できない (近傍は区別する)。
* L2 多重散乱による樹冠内の拡散光は未実装。深い樹冠の下面はこのモデルでは暗くなる (拡散成分の分だけ過小評価になり得る。数値は未検証)。
* L3 隠れセル規則は K=4。厚さ 9 m 超の塊の中心は空気扱い (漏れる側)、小さな密閉空洞は葉扱い (暗くなる側)。
* L4 太陽が水平線近くで格子を横切る場合、格子外の遮蔽は近傍計算が見ない。
* L5 モブは太陽透過を遮らない。
* L6 テクスチャの穴 (α<0.1) はシャドウマップ側にあるため、遠方推定では穴に応じて明滅し得る。近傍の格子には穴の情報が無く、樹冠は一様に減衰する。

## 再現手順
* `python3 -I reports/2026-11-21-leaf-light/solver/verify_tree.py .` 基底ツリーとの差分・image 数・不変ファイルを確認。
* `python3 -I reports/2026-11-21-leaf-light/solver/leaf_reference.py` 仕様の CPU 再記述。
* `python3 -I reports/2026-11-21-leaf-light/solver/build_release.py . build/Aqualumen-1.8.0-leaf-rc1.zip` 不変 ZIP の作成。
