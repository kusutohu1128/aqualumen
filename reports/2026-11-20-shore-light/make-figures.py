"""Rebuild comparison panels and count matched ray classes from captured Minecraft frames."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
r=Path(__file__).resolve().parent
after='delivery-1440p'
def opened(role,scene):
    return Image.open(r/role/'capture'/(scene+'.png')).convert('RGB')
def fixed(role,scene):
    return json.loads((r/role/'capture'/(scene+'.json')).read_text())
def font(size):
    return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc',size,index=0)
def board(name,labels,scenes,sources,w):
    pad=14;h=w*9//16;head=50;sub=39
    out=Image.new('RGB',(pad+(w+pad)*len(labels),head+len(scenes)*(sub+h+pad)),(18,26,31));d=ImageDraw.Draw(out)
    for i,label in enumerate(labels):d.text((pad+i*(w+pad),7),label,font=font(23),fill=(230,240,241))
    for j,(scene,display) in enumerate(scenes):
        y=head+j*(sub+h+pad)
        d.text((pad,y),display,font=font(18),fill=(133,211,203))
        for i,src in enumerate(sources):
            role=src.get(scene,src['default']);data=fixed(role,scene)
            assert data['camera_follows_local_player'] and data.get('camera_eye_match',True) and data['shader_active'] and not data['shader_fallback']
            if i==0:camera=data['actual_camera_position'];rotation=data['actual_camera_rotation']
            else:assert np.max(np.abs(np.array(camera)-data['actual_camera_position']))<.02 and np.max(np.abs(np.array(rotation)-data['actual_camera_rotation']))<.02
            im=opened(role,scene).resize((w,h),Image.Resampling.LANCZOS);out.paste(im,(pad+i*(w+pad),y+sub))
    out.save(r/name,quality=93)
scenes=[('underwater-shore-view','水面の下から見た砂の段差'),('coast-day','昼の浅瀬と沖'),('ground-evening','夕方の柵・石段・対岸の映り込み'),('ocean-rain','雨の海')]
board('comparison.jpg',['Aqualumen 1.0.1','Aqualumen 1.1.0'],scenes,[{'default':'native-before'},{'default':after}],680)
board('reference-comparison.jpg',['Aqualumen 1.1.0','Photon v1.1','Complementary Unbound r5.4'],scenes[:3],[{'default':n} for n in (after,'photon_v1.1','ComplementaryUnbound_r5.4')],520)
out=Image.new('RGB',(1240,780),(18,26,31));d=ImageDraw.Draw(out)
for i,(name,scene) in enumerate([('夕日と海面の反射','ocean-sun-dusk'),('浅瀬に落ちる雨','coast-rain-close'),('水深3.25 mで真上を向く','underwater-up-deep'),('日中の石段と波打ち際','ground-noon')]):
    x=10+(i%2)*615;y=8+i//2*385;d.text((x,y),name,font=font(21),fill='white');out.paste(opened(after,scene).resize((605,340),Image.Resampling.LANCZOS),(x,y+36))
out.save(r/'gallery.jpg',quality=92)
out=Image.new('RGB',(1220,355),(18,26,31));d=ImageDraw.Draw(out)
for i,role in enumerate(['native-before',after]):
    im=opened(role,'ground-evening');w,h=im.size;crop=im.crop(tuple(round(n*w/960) for n in (255,275,745,527)));crop=crop.resize((600,308),Image.Resampling.LANCZOS)
    x=6+i*607;d.text((x,2),['1.0.1　岸の白い帯','1.1.0　砂利と土の境界'][i],font=font(21),fill='white');out.paste(crop,(x,37))
out.save(r/'bank-detail.jpg',quality=93)
old=np.array(opened('routes','underwater-shore-view'));new=np.array(opened('delivery-hits','underwater-shore-view'))
miss=(old[...,0]>230)&(old[...,1]<25)&(old[...,2]<25)
hit=(new[...,1]>230)&(new[...,0]<25)&(new[...,2]<25)
pure=(new==[0,255,0]).all(axis=2);red=(new[...,0]>230)&(new[...,1]<25)&(new[...,2]<25)
roi=np.zeros(miss.shape,bool);roi[285:390,560:760]=True
ret={}
for name,mask in [('centralBounds560_285_760_390',roi),('wholeFrame',np.ones_like(roi))]:
    was=miss&mask;ret[name]={'previousMiss':int(was.sum()),'newGreen':int((was&hit).sum()),'pureGreen':int((was&pure).sum()),'stillRed':int((was&red).sum())}
out=Image.new('RGB',(1240,405),(18,26,31));d=ImageDraw.Draw(out)
for i,(role,tit) in enumerate([('routes','1.0.1　赤 = 反射先なし'),('delivery-hits','1.1.0　緑 = 近傍の実ブロック面')]):
    img=opened(role,'underwater-shore-view');dr=ImageDraw.Draw(img);dr.rectangle((560,285,759,389),outline='white',width=2);x=9+i*615;d.text((x,5),tit,font=font(21),fill='white');out.paste(img.resize((605,340),Image.Resampling.NEAREST),(x,43))
out.save(r/'receiver-comparison.png')
(r/'receiver-counts.json').write_text(json.dumps(ret,indent=2)+'\n')
print(ret)
