from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
from io import BytesIO
import json,zlib,re,base64
p=Path(__file__).resolve().parent
files=['colab-out.log','colab-err.log','local-out.log']
for filename in files:
 f=p/filename
 if not f.exists():continue
 mat=re.search(rb'AQL_RESULT_([a-zA-Z0-9+/=]+)_END_RESULT',f.read_bytes())
 if mat:break
else:raise RuntimeError('Calculation result unavailable')
o=json.loads(zlib.decompress(base64.b64decode(mat.group(1))))
regular='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font=ImageFont.truetype(regular,19);small=ImageFont.truetype(regular,14)
indices=[0,7,15,23,30]
intro='金鉱石 / 固定視点・計算画像'
def tile(row,scale):
 return Image.open(BytesIO(base64.b64decode(row[0]))).resize((scale,scale),Image.Resampling.NEAREST)
sheet=Image.new('RGB',(1060,520),'#171819');d=ImageDraw.Draw(sheet)
d.text((12,6),intro,font=font,fill='white');d.text((12,42),'左から右へ灯りを移動　　上段：金属反射あり / 下段：同一色の対照',font=small,fill='#bac2c6')
for col,i in enumerate(indices):
 x=10+col*210
 d.text((x,70),f'{o["angles"][i]:+d}°',font=small,fill='white')
 for j,k in enumerate(('facets','control')):
  sheet.paste(tile(o[k][i],202),(x,95+j*209))
sheet.save(p/'Gold-reference.png')
frames=[]
for i,angle in enumerate(o['angles']):
 frame=Image.new('RGB',(648,362),'#171819');fd=ImageDraw.Draw(frame)
 fd.text((8,3),'金属反射あり',font=font,fill='white');fd.text((332,3),'対照',font=font,fill='white');fd.text((435,7),f'灯り {angle:+d}°・計算画像',font=small,fill='white')
 frame.paste(tile(o['facets'][i],318),(4,36));frame.paste(tile(o['control'][i],318),(326,36))
 frames.append(frame)
frames[0].save(p/'Gold-reference.gif',save_all=True,append_images=frames[1:]+frames[-2:0:-1],duration=75,loop=0)
peaks=[r[1] for r in o['facets']]
summary={'backend':'Colab CPU' if filename.startswith('colab') else 'Local CPU','quantity':'added GGX specular irradiance in relative linear luminance','fixedEye':[0,0,2.5],'wall':'1 block, 32x32 texels','anglesDegrees':o['angles'],'facets':peaks,'control':[r[1] for r in o['control']],'uniquePeakPositions':len(set(tuple(r['dominantTexel']) for r in peaks)),'note':'Isolated shader material term: coverage=visibility=1, single warm torch at radius 2 blocks. Ambient, camera response, and wall are reference-fixture approximations.'}
(p/'Gold-reference.json').write_text(json.dumps(summary,indent=2))
print(summary['backend'],summary['uniquePeakPositions'],[peaks[i]['dominantTexel'] for i in indices])
