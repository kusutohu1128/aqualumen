"""Decode the diagnostic pixels in the real game's final framebuffer."""
from pathlib import Path
import json
from PIL import Image
r=Path(__file__).resolve().parent/'captured-shore-slots'
cert=json.loads((r/'complete.json').read_text())
rows={}
for name in cert['screenshots']:
    im=Image.open(r/(name+'.png')).convert('RGB')
    def byte(cx,cz):
        patch=im.crop((cx*16+5,im.height-cz*16-11,cx*16+11,im.height-cz*16-5))
        pix={patch.getpixel((px,py)) for px in range(patch.width) for py in range(patch.height)}
        assert len(pix)==1, (name,cx,cz,pix)
        v,g,b=pix.pop()
        assert (g,b)==(0,255), (name,cx,cz,v,g,b)
        return v
    cells=[]
    for z in range(3):
        for x in range(3):
            cells.append(dict(x=201+x,z=360+z,path=byte(x,z),floor=byte(4+x,z),corners=[byte(4*corner+x,4+z) for corner in range(4)]))
    rows[name]=cells
def active(cells):return sum(c['path']!=0 for c in cells)
sizes={n:active(c) for n,c in rows.items()}
floor_ok=all(sum(c['floor']>0 for c in rows[n])==9 for n in ('dark','dark-pillar','dark-again'))
mask_ok=all(k.startswith('one') and sizes[k]==1 or k.startswith('nine') and sizes[k]==9 or k.startswith('dark') and sizes[k]==0 for k in sizes)
tops_ok=all(all(min(c['corners'])>0 for c in cells if c['path']) for cells in rows.values())
(r/'faces.json').write_text(json.dumps(dict(pack=cert['sha256'],renderer=cert['renderer'],activeCells=sizes,floorControl=floor_ok,materialObserved=mask_ok,
                                           allFourHeights=tops_ok,sourceHeightDecode='(code-1)/240 blocks',samples=rows),indent=2)+'\n')
print('lava cells by world state',sizes,'solid positive control',floor_ok,'all matched',mask_ok,'all four corners',tops_ok)
