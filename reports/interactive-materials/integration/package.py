from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
here=Path(__file__).resolve().parent
study=here.parent
repo=study.parents[1]
parts={ 'shaderpacks/Aqualumen-Interactive-Materials.zip':here/'Aqualumen-Interactive-Materials.zip',
        'resourcepacks/Aqualumen-Gold-Faceted-32x.zip':study/'gold-art/Aqualumen-Gold-Faceted-32x.zip',
        'controls/Aqualumen-Gold-Control-32x.zip':study/'gold-art/Aqualumen-Gold-Control-32x.zip',
        'mods/aqualumen-lighting-compiler-0.3.0.jar':repo/'dist/aqualumen-lighting-compiler-0.3.0.jar',
        'LICENSE-Aqualumen.txt':repo/'LICENSE'}
readme='''Aqualumen Interactive Materials　Minecraft Java 1.21.1用の試作
環境：Fabric、Iris 1.8.8、Sodium 0.6.9、Aqualumen 1.9.0-preview.10 系列。

導入
外側のZIPを展開し、shaderpacks と resourcepacks 内の ZIP はそのまま各フォルダーにコピーします。
NVIDIAの既存 Aqualumen Lab 環境ではコンパイル用Mod 0.3.0を有効にします。同じModが導入済みの場合は既存のものを使います。
ゲームで Aqualumen-Interactive-Materials と Aqualumen-Gold-Faceted-32x の両方を選択します。
既存の水面との接触による波は Aqualumen の対応する物理Mod/ゲーム設定に依存します。

試す場所
金鉱石：暗い場所に通常の石の金鉱石と松明を置き、光源の反対側を横に歩きます。
同じ色柄で見比べる場合は controls 内のリソースパックに切り替えてください。光沢は金の部分に限定されます。
銅の格子：暗い部屋で、ランタンから明るい壁へ向かう途中に銅の格子を置きます。色ガラスや魂のランタンを加えて比較できます。
水面：日光の入る小さな水場に、近くの張り出した天井を設けます。試作はカメラ付近の静水の上面と、下向きの天井面を対象にしています。
'''
out=here/'Aqualumen-Materials-Kit.zip'
with ZipFile(out,'w',ZIP_DEFLATED) as z:
    z.writestr('README-ja.txt',readme)
    for k,p in parts.items():z.write(p,k)
with ZipFile(out) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(k)).digest()==hashlib.sha256(p.read_bytes()).digest() for k,p in parts.items())
print(out)
