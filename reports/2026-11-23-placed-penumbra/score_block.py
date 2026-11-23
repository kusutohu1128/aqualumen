"""Find on-screen cell boundaries beyond the outer rim of a one-cube penumbra."""
from score import *
from single_block import CUBES

def assess(folder,stage,cell,across=False):
    path=folder/(stage+"-ingame.png")
    digest=check_record(folder,path)
    rgb=np.asarray(Image.open(path).convert("RGB"))
    assert np.array_equal(rgb[-3,:256],np.repeat(np.arange(256)[:,None],3,axis=1))
    a=rgb[:-5,:rgb.shape[1]//12*12].reshape(rgb.shape[0]-5,-1,2,6,3)
    if across:
        a=rgb[::-1].reshape(-1,2,6,rgb.shape[1],3)[1:].transpose(3,0,1,2,4)
    def scalar(v):return v.astype(np.int32)@np.array([1,256,65536])
    light=a[:,:,:,0];p=scalar(a[:,:,:,1:4])/65536.+ROOM_ANCHOR
    bias=(a[:,:,:,4].astype(float)+256*a[:,:,:,5].astype(float))/1048576.-.03
    x,y,z=np.moveaxis(p,-1,0)
    face=(abs(y-151)<.002)&(x>403)&(x<411)&(z> -413)&(z< -404)
    flags=light[:,:,:,2];valid=face&(flags>=64)&((flags&12)==0)&(abs(bias[:,:,:,1]-.025)<.001)
    grid=np.zeros((64,64,64),np.uint8);grid[tuple(cell-ROOM_ANCHOR)]=1
    ref=integral(p,np.full(valid.shape,4,np.uint8),valid,ROOM_SOURCE[0],ROOM_ANCHOR,grid,bias)
    old=light[:,:,:,0]/255.;new=light[:,:,:,1]/255.
    cube=np.floor(p+bias).astype(int)
    key=(cube[:,:,:,0]-400)*32+cube[:,:,:,2]+416
    soft=(ref>.005)&(ref<.995)
    softCells=np.unique(key[soft])
    near=np.isin(key,softCells)
    row=dict(sha=digest,partial=int(soft.sum()),partialCells=len(softCells),
             partialErrors=[moments(abs(q-ref)[soft]) for q in (old,new)])
    for label,axis in (("horizontal" if across else "vertical",0),("vertical" if across else "horizontal",2)):
        def both(v):return np.take(v,range(v.shape[axis]-1),axis=axis),np.take(v,range(1,v.shape[axis]),axis=axis)
        l,r=both(ref);k1,k2=both(key);c1,c2=both(near);p1,p2=both(p)
        boundary=(l>=0)&(r>=0)&(k1!=k2)&(np.linalg.norm(p1-p2,axis=-1)<.06)
        for condition,sel in (("clearBeyondPenumbra",boundary&(l==1)&(r==1)&(c1|c2)),
                              ("allPartialEdges",boundary&((l>.005)&(l<.995)|(r>.005)&(r<.995)))):
            err=[abs(np.diff(q,axis=axis)-(r-l))[sel] for q in (old,new)]
            row[label+"-"+condition]=dict(pairs=int(sel.sum()),errors=[moments(q) for q in err],
                                         excessOverTwoBytes=[int((q>2/255.).sum()) for q in err])
    return row

if __name__=="__main__":
    across=sys.argv[1:]==["--across"]
    folder=HERE/("one-block-horizontal" if across else "one-block-at-night")
    stages=json.loads((folder/"complete.json").read_text())["stages"]
    report={n:assess(folder,n,np.array(CUBES[n]),across) for n in stages}
    (HERE/("one-block-horizontal.json" if across else "one-block.json")).write_text(json.dumps(report,indent=2)+"\n")
