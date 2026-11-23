from pathlib import Path
from zipfile import ZipFile
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import sys, struct, statistics, json
here=Path(__file__).resolve().parent
if sys.argv[1]=='prepare':
 jar=next(Path.home().glob('.var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/libraries/com/mojang/minecraft/1.21.1/*.jar'))
 with ZipFile(jar) as z: tex=Image.open(BytesIO(z.read('assets/minecraft/textures/block/copper_grate.png'))).convert('RGBA')
 assert tex.size==(16,16)
 masks=[0]*(16*120)
 masks[16*104]=1
 for y in range(16): masks[16*105+y]=sum(int(tex.getpixel((x,y))[3]>=26)<<x for x in range(16))
 (here/'mask.bin').write_bytes(struct.pack('<1920I',*masks))
 src=(here/'grate_transmission.glsl').read_text()
 local=(here/'candidate/shaders/lib/local_lighting.glsl').read_text()
 glass=local[local.index('vec3 lampGlass('):local.index('// At simultaneous')]
 (here/'probe.comp').write_text("""#version 450
 layout(local_size_x=8,local_size_y=8) in;
 layout(binding=0) uniform usampler2D aqualumenDoorMask;
 layout(std430,binding=0) buffer Output {uint values[];};
 """+src+glass+"""
 float visible(vec2 origin, vec2 light,int mode){
    // Receiver z=-1.2, grate z=0..1, lamp z=3. Both ends are outside.
    vec2 front=mix(origin,light,1.2/4.2),back=mix(origin,light,2.2/4.2);
    if(any(lessThan(front,vec2(0)))||any(greaterThanEqual(front,vec2(1)))||
       any(lessThan(back,vec2(0)))||any(greaterThanEqual(back,vec2(1))))return 0.;
    if(mode==0) return 1.;
    return grateBlocks(11|(63<<9),vec3(front,0),vec3(back,1))?0.:1.;
 }
 void main(){
    uvec3 p=gl_GlobalInvocationID;
    vec2 uv=(vec2(p.xy)+.5)/512.,pos=vec2(.5)+(uv-.5)*1.55;
    vec3 energy=vec3(0);
    for(int i=0;i<32;i++){
      // Equal-area samples of a small circular emitter, projected onto the plate.
      float a=2.39996323*float(i),r=.065*sqrt((float(i)+.5)/32.);
      vec2 offset=r*vec2(cos(a),sin(a));
      vec2 warm=vec2(.45,.45)+offset;
      vec3 color=vec3(1.,.49,.19);
      if(p.z==2u) color*=pow(lampGlass(14),vec3(length(vec3(warm-pos,4.2))/4.2));
      energy+=visible(pos,warm,int(p.z))*color;
      if(p.z==3u)energy+=visible(pos,vec2(.595,.49)+offset,1)*vec3(.11,.65,1.);
    }
    vec3 rgb=pow(clamp(energy/32.+.012,0.,1.),vec3(1./2.2));
    values[p.x+512u*(p.y+512u*p.z)]=packUnorm4x8(vec4(rgb,1));
 }
 """)
else:
 raw=(here/'projection.bin').read_bytes();font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
 sheet=Image.new('RGB',(1080,1180),'#191d20');d=ImageDraw.Draw(sheet)
 d.text((22,10),'銅格子を通る光  /  透過計算の試験',font=ImageFont.truetype(font,35),fill='white')
 d.text((24,66),'平面スクリーンへの投影　Mesaソフトウェア描画・ゲーム画面外',font=ImageFont.truetype(font,22),fill='#cccccc')
 stats={}
 for i,title in enumerate(['開口のみ','銅格子','格子 ＋ 赤色ガラス','格子 ＋ 暖色と魂色の二灯']):
  im=Image.frombytes('RGBA',(512,512),raw[i*512*512*4:(i+1)*512*512*4]).convert('RGB')
  x,y=20+530*(i%2),110+532*(i//2)
  d.text((x,y),title,font=ImageFont.truetype(font,24),fill='white')
  sheet.paste(im.resize((490,490),Image.Resampling.LANCZOS),(x,y+35))
  ch=list(zip(*im.getdata()));stats[title]=dict(red=statistics.mean(ch[0]),green=statistics.mean(ch[1]),blue=statistics.mean(ch[2]),bright=sum(1 for r in ch[0] if r>80))
 vals=list(stats.values());assert vals[0]['bright']>vals[1]['bright']>0
 assert vals[2]['green']<vals[1]['green'] and vals[3]['blue']>vals[1]['blue']
 sheet.save(here/'projection-preview.jpg',quality=95)
 (here/'probe-stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
