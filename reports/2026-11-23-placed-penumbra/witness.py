"""Plot one actual screen-space scan through the measured forest seam."""
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from score import HERE,DENSITY,WORK,unpack,worldgrid,face_from_geometry,integral,FOREST_ANCHOR,FOREST_SOURCES

def main():
    crops=["gp-density-placed-penumbra-meter","gp-density-placed-hull-meter"]
    readings=[unpack(DENSITY/run/"birch-4-ingame.png",2) for run in crops]
    col=1440//8;y0,y1=988,1020
    m,p,n=readings[0]
    p=p[y0:y1+1,col:col+1];face=face_from_geometry(p,np.array([208.5,65.62,355.5]))
    ref=integral(p,face,np.ones(face.shape,bool),FOREST_SOURCES[1],FOREST_ANCHOR,worldgrid())[:,0]
    assert (ref>=0).all()
    curves=[ref,m[y0:y1+1,col,1,0]/255,m[y0:y1+1,col,1,1]/255,readings[1][0][y0:y1+1,col,1,1]/255]
    img=Image.new("RGB",(970,445),"#faf8f3")
    draw=ImageDraw.Draw(img)
    def font(n):return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",n)
    draw.text((32,15),"Torch visibility across one block boundary",font=font(25),fill="#1f2931")
    x0,xend,top,bottom=87,920,95,368
    def x(j):return x0+(xend-x0)*j/(y1-y0)
    def y(value):return bottom-(bottom-top)*value
    for i in range(5):
        v=i*.25;draw.line((x0,y(v),xend,y(v)),fill="#d8d7cf")
        draw.text((23,y(v)-8),str(round(v*100))+"%",font=font(15),fill="#384348")
    for a in (988,996,1004,1012,1020):
        draw.text((x(a-y0)-21,bottom+7),str(a),font=font(15),fill="#384348")
    bx=x(1003.5-y0)
    for i in range(top,bottom,12):draw.line((bx,i,bx,i+6), fill="#818681",width=1)
    colors=["#183a4e","#966525","#ca5351","#008a73"]
    for k,v in enumerate(curves):
        pts=[(x(i),y(q)) for i,q in enumerate(v)]
        if k<3:draw.line(pts,fill=colors[k],width=4 if k==0 else 2)
        else:
            for xx,yy in pts:draw.ellipse((xx-2.5,yy-2.5,xx+2.5,yy+2.5),fill=colors[k])
    for xx,name,color in zip([65,299,496,701],["8,192-ray reference","Previous build","Initial box cache","Revised cache"],colors):
        draw.line((xx,69,xx+23,69),fill=color,width=3);draw.text((xx+29,59),name,font=font(16),fill="#1f2931")
    draw.text((335,405),"Vertical screen coordinate at x = 1440 (px)",font=font(16),fill="#384348")
    img.save(HERE/"forest-edge.png")
if __name__=="__main__":main()
