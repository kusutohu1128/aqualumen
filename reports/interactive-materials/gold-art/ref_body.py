from PIL import Image
from io import BytesIO
from zipfile import ZipFile
import base64,math,json
F=ZipFile(BytesIO(base64.b64decode(FACETED)))
C=ZipFile(BytesIO(base64.b64decode(CONTROL)))
path='assets/minecraft/textures/block/gold_ore'
def load(z):
 return [Image.open(BytesIO(z.read(path+s+'.png'))) for s in ('','_n','_s')]
def dot(u,v):return sum(a*b for a,b in zip(u,v))
def unit(v):
 d=math.sqrt(dot(v,v));return [x/d for x in v]
def lit(n,view,l,rough,angular):
 h=unit([a+b for a,b in zip(l,view)])
 nl,nv=dot(n,l),dot(n,view)
 if min(nl,nv)<=0:return [0]*3
 nh=max(dot(n,h),0)
 a=.34+(.16-.34)*rough
 a2=min(1,a*a+angular)
 f=nh*nh*(a2-1)+1
 D=a2/(3.141593*f*f)
 vis=.5/max(nl*math.sqrt(nv*nv*(1-a2)+a2)+nv*math.sqrt(nl*nl*(1-a2)+a2),.001)
 t=(1-max(dot(view,h),0))**5
 return [(f0+(1-f0)*t)*D*vis*nl*.72 for f0 in (.95,.70,.29)]
def sample(maps,deg):
 angle=math.radians(deg)
 lamp=[2*math.sin(angle),.20,2*math.cos(angle)]
 im=Image.new('RGB',(32,32)); metrics=[]
 for y in range(32):
  for x in range(32):
   p=[(x+.5)/32-.5,.5-(y+.5)/32,0]
   delta=[a-b for a,b in zip(lamp,p)]
   view=unit([-p[0],-p[1],2.5])
   l=unit(delta);d2=dot(delta,delta)
   base=[(k/255)**2.2 for k in maps[0].getpixel((x,y))]
   nr=maps[1].getpixel((x,y)); s=maps[2].getpixel((x,y)); marked=s[1]==231
   nx,ny=[k/255*2-1 for k in nr[:2]];n=unit([nx,ny,math.sqrt(max(1-nx*nx-ny*ny,.001))])
   spec=lit(n,view,l,min(max((s[0]/255-.5)*2,0),1),.13*.13/(4*max(d2,.1))) if marked else [0]*3
   energy=[t*11/(.38+d2) for t in (1,.49,.19)]
   glint=[e*k for e,k in zip(energy,spec)]
   luminance=dot(glint,[.2126,.7152,.0722])
   metrics.append((luminance,x,y))
   rgb=[a*(1-.4*.72*marked)*(.22+e*l[2])+g for a,e,g in zip(base,energy,glint)]
   im.putpixel((x,y),tuple(round(255*(c/(1+c))**(1/2.2)) for c in rgb))
 peak=max(metrics)
 return im, {'dominantTexel':list(peak[1:]) if peak[0] else None,'peakGoldLuminance':round(peak[0],5),'nonzeroSpecularTexels':sum(k>0 for k,_,_ in metrics)}
def encode(im):
 b=BytesIO();im.save(b,'PNG');return base64.b64encode(b.getvalue()).decode()
o={'angles':list(range(-60,61,4))}
for name,pack in [('facets',F),('control',C)]:
 maps=load(pack); o[name]=[]
 for deg in o['angles']:
  im,stats=sample(maps,deg);o[name].append([encode(im),stats])
assert len({tuple(row[1]['dominantTexel']) for row in o['facets']})>=3
assert not any(row[1]['nonzeroSpecularTexels'] for row in o['control'])
print('AQL_RESULT_'+base64.b64encode(__import__('zlib').compress(json.dumps(o).encode())).decode()+'_END_RESULT')
