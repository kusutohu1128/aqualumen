"""CPU forward mapping of a sampled water heightfield onto a planar cave ceiling.
Coordinate units are blocks and seconds. Run with numpy and Pillow installed.
"""
from pathlib import Path
import json, subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
P=Path(__file__).parent
W,H=800,426
FPS=24
TOP=2.8
XMIN,XMAX,ZMIN,ZMAX=-4.,4.,-5.,4.
AP=(-2.9,-.15,-2.9,-.7)
SUN=np.array([.62,-1.,.32])
SUN/=np.linalg.norm(SUN)
fontfile='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def font(n):return ImageFont.truetype(fontfile,n)
F={'top':font(20),'cap':font(19),'small':font(15)}
def norm(a): return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-7)
def aperture(x,z):return (x>=AP[0])&(x<AP[1])&(z>=AP[2])&(z<AP[3])
def topopening(t):return not 6.5<=t<8.25
def sample_water(x,z,t,waves=True):
 h=.005*np.sin(5*x+2.1*z-.8*t)+.003*np.cos(3.8*z-1.4*x+.9*t)
 if waves:
  for start,sx,sz,amp in [(1.6,-.2,-1.1,.052),(2.5,.24,-.82,.045)]:
   dt=t-start
   if dt<=0:continue
   r=np.sqrt((x-sx)**2+(z-sz)**2+.017)
   dr=r-1.24*dt
   h+=amp*(1-np.exp(-5*dt))*np.exp(-.22*dt)*np.exp(-(dr/.58)**2)*np.cos(11*dr)/np.sqrt(1+.85*r)
 return h
N=240
x,z=np.meshgrid(np.arange(-1.55,2.11,.0085),np.arange(-2.31,.68,.0085))
def accumulate(t,open_window=True,waves=True):
 if not open_window:return np.zeros((N,N))
 h=sample_water(x,z,t,waves)
 dz,dx=np.gradient(h,.0085)
 n=norm(np.stack([-dx,np.ones_like(dx),-dz],-1))
 cos_i=np.maximum(0,-np.einsum('ijk,k->ij',n,SUN))
 ref=SUN+2*cos_i[...,None]*n
 dist=(TOP-h)/np.maximum(ref[...,1],.01)
 hx=x+dist*ref[...,0]; hz=z+dist*ref[...,2]
 entry_x=x+(TOP-h)*SUN[0]/SUN[1];entry_z=z+(TOP-h)*SUN[2]/SUN[1]
 mask=aperture(entry_x,entry_z)&(~aperture(hx,hz))&(ref[...,1]>.01)&(hx>=XMIN)&(hx<XMAX)&(hz>=ZMIN)&(hz<ZMAX)
 # Schlick water-to-air interface viewed from air, incl. projected incident power.
 fres=.0204+.9796*(1-cos_i)**5
 energy=(fres*cos_i/n[...,1]*.0085**2/((XMAX-XMIN)*(ZMAX-ZMIN)/N**2))[mask]
 u=((hx[mask]-XMIN)/(XMAX-XMIN)*N)-.5;v=((hz[mask]-ZMIN)/(ZMAX-ZMIN)*N)-.5
 ix=np.floor(u).astype(int);iz=np.floor(v).astype(int);fx=u-ix;fz=v-iz
 acc=np.zeros(N*N)
 for ox,wx in [(0,1-fx),(1,fx)]:
  for oz,wz in [(0,1-fz),(1,fz)]:
   i=ix+ox;j=iz+oz
   valid=(i>=0)&(i<N)&(j>=0)&(j<N)
   acc+=np.bincount((j[valid]*N+i[valid]),weights=(energy*wx*wz)[valid],minlength=N*N)
 return acc.reshape(N,N)
def sample_light(m,x,z):
 u=np.clip((x-XMIN)/(XMAX-XMIN)*N-.5,0,N-1.01);v=np.clip((z-ZMIN)/(ZMAX-ZMIN)*N-.5,0,N-1.01)
 i=u.astype(int);j=v.astype(int);a=u-i;b=v-j
 return (1-b)*((1-a)*m[j,i]+a*m[j,i+1])+b*((1-a)*m[j+1,i]+a*m[j+1,i+1])
def pseudo(x,y):
 return np.mod(np.sin(x*127.1+y*311.7)*43758.5453,1.)
def rock(u,v):
 # World-locked, hand-defined 16-pixel limestone strata pattern across a block grid.
 U=np.floor(u*16)/16;V=np.floor(v*16)/16
 grain=pseudo(np.floor(U*6),np.floor(V*7))*.05+pseudo(U,V)*.045
 bedding=.046*np.sin(5.8*V+1.8*np.sin(2.4*U+.35*V))+.022*np.cos(8*U+3*V)
 tone=.42+grain+bedding
 return tone[...,None]*np.array([.94,.91,.83])
def setup_view():
 cx,cy,cz=-.75,1.08,-4.45
 target=np.array([1.30,2.42,.25]);forward=norm(target-np.array([cx,cy,cz]))
 right=norm(np.cross([0.,1.,0.],forward));up=np.cross(forward,right)
 py,px=np.mgrid[0:H,0:W]
 dirs=norm(forward+(2*(px+.5)/W-1)[...,None]*right*.90+(1-2*(py+.5)/H)[...,None]*up*.90*H/W)
 plane=np.where(dirs[...,1]>0,TOP,0)
 ty=(plane-cy)/np.where(abs(dirs[...,1])<1e-6,1e-6,dirs[...,1])
 tx=(np.where(dirs[...,0]>0,XMAX,XMIN)-cx)/np.where(abs(dirs[...,0])<1e-6,1e-6,dirs[...,0])
 tz=(ZMAX-cz)/dirs[...,2]
 dd=np.minimum(ty,np.minimum(tx,tz));points=np.array([cx,cy,cz])+dd[...,None]*dirs
 xp,yp,zp=points.transpose(2,0,1);ceil=(dd==ty)&(dirs[...,1]>0);water=(dd==ty)&(~ceil);hole=ceil&aperture(xp,zp)
 # Outcrops at the rear of the cave are outside the light bundle.
 surface=np.where(dd==ty,1,np.where(dd==tx,0,2))
 for lo,hi in [((-4,0,2.5),(-1,1,4)),((-1,0,3),(1,.5,4)),((1,0,3),(3,1,4)),((3,0,2),(4,1.5,4)),
               ((-4,1,3.4),(-2,1.5,4)),((2,1,3.5),(4,1.5,4))]:
  a=(np.array(lo)-[cx,cy,cz])/dirs;b=(np.array(hi)-[cx,cy,cz])/dirs
  near=np.minimum(a,b);enter=near.max(axis=-1); leave=np.maximum(a,b).min(axis=-1)
  hit=(enter>0)&(leave>=enter)&(enter<dd)
  dd=np.where(hit,enter,dd);surface=np.where(hit,np.argmax(near,axis=-1),surface)
  ceil&=~hit;water&=~hit;hole&=~hit
 pts=np.array([cx,cy,cz])+dd[...,None]*dirs;xp,yp,zp=pts.transpose(2,0,1)
 u=np.where(surface==0,zp,xp);v=np.where(surface==1,zp,yp)
 material=rock(u,v)
 occ=1-.25*np.exp(-np.minimum(XMAX-abs(xp),ZMAX-zp).clip(0)*2.8)
 wall_tone=np.where(surface==1,.29,np.where(surface==0,.16,.195))
 ambient=material*np.where(ceil,.17,np.where(water,.065,wall_tone))[...,None]*np.array([.70,.82,1.])*occ[...,None]
 return xp,yp,zp,ceil,water,hole,material,ambient
xp,yp,zp,ceil,water,hole,material,ambient=setup_view()
# Fixed ceiling UVs; sample only visible receiver pixels on each frame.
xx,zz=xp[ceil],zp[ceil]
def render(t):
 opened=topopening(t)
 field=accumulate(t,opened)
 rgb=ambient.copy()
 rgb[ceil]+=material[ceil]*sample_light(field,xx,zz)[:,None]*np.array([21,17,11])
 if opened:
  rim=np.minimum.reduce([xp-AP[0],AP[1]-xp,zp-AP[2],AP[3]-zp])
  exposure=(.63+.24*np.clip(rim*4,0,1))[...,None]
  rgb[hole]=(exposure*np.array([.76,.91,1.]))[hole]
  soft=np.exp(-((xp+.9)**2+(zp+1.6)**2)*.42)
  rgb[~hole]+=(material*soft[...,None]*np.array([.07,.075,.08]))[~hole]
 # The visible bottom strip indicates a shallow pool; sky light footprint changes with skylight.
 xw=xp[water];zw=zp[water];h=sample_water(xw,zw,t)
 if opened:
  lit=aperture(xw+TOP*SUN[0]/SUN[1],zw+TOP*SUN[2]/SUN[1])
  rgb[water]+=lit[:,None]*(.32+h[:,None])*np.array([.45,.85,.90])
 rgb[water]+=np.clip(.035+h*2,0,.13)[:,None]*np.array([.27,.64,.73])
 out=(np.power(np.clip(rgb,0,1),1/2.2)*255).astype('uint8')
 return Image.fromarray(out),field
def compose(t):
 panel,field=render(t)
 out=Image.new('RGB',(800,500),'#111c21');out.paste(panel,(0,39));d=ImageDraw.Draw(out)
 d.text((17,3),'水面から天井に返る光　 /　 CPU 光学試作',font=F['top'],fill='#f3eee1')
 d.text((640,7),f'{t:04.1f} s    /   10 s',font=F['small'],fill='#b4c5c4')
 label=('天窓からの日光　・　静かな水面' if t<1.6 else '水面に二回接触　・　波が反射光を動かす' if t<6.5 else '天窓を閉じる　・　反射光が消える' if t<8.25 else '天窓を開く　・　反射光が戻る')
 d.text((16,467),label,font=F['cap'],fill='#f2dfb8')
 return out,field
def main():
 proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size','800x500','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(P/'ceiling-caustics.mp4')],stdin=subprocess.PIPE)
 stats={}
 for i in range(10*FPS):
  t=i/FPS
  im,f=compose(t);proc.stdin.write(im.tobytes())
  if i in (24,72,168,216):
   im.save(P/('frame-%03d.jpg'%i),quality=92)
   stats[str(t)]={'sum':round(float(f.sum()),5),'peak':round(float(f.max()),5)}
 proc.stdin.close();assert proc.wait()==0
 ordinary=accumulate(3.,True,False)
 disturbed=accumulate(3.,True,True)
 diff=float(np.sum(np.abs(disturbed-ordinary))/np.sum(ordinary))
 assert stats['7.0']['sum']==0 and stats['1.0']['sum']>0 and diff>.1
 print(json.dumps({'frames':10*FPS,'size':[800,500],'fps':FPS,'receiverMap':stats,'sameTimeDisturbanceRelativeL1':diff},indent=2))
if __name__=='__main__':main()
