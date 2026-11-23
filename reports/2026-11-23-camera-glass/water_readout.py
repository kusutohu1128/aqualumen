"""Evaluate foreground radiance and the independent water-to-bed path."""
import json
from readout import HERE,RED,measure,Image,np,math
water=HERE/'water-meter'
assert json.loads((water/'complete.json').read_text())['complete']
m={n:measure(water/(n+'-ingame.png')) for n in ('pool','front-pane','rear-pane','pool-cleared')}
goal=RED**(.125/math.cos(math.radians(47)))
assert np.max(np.abs(m['front-pane']['median']-goal))<.012
for name in ('pool','rear-pane','pool-cleared'):
    assert np.min(m[name]['p10'])>.98
(HERE/'water-surface.json').write_text(json.dumps(dict(surface=m,expectedFront=goal.tolist()),indent=2)+'\n')
sub=HERE/'underwater-path'
if (sub/'complete.json').exists():
    assert json.loads((sub/'complete.json').read_text())['complete']
    data={}
    for stage in ('pool','submerged','pool-cleared'):
        im=np.asarray(Image.open(sub/(stage+'-ingame.png')).convert('RGB'),dtype=float)
        # Avoid the diagnostic HUD, tank walls and refracted image limits.
        h,w,_=im.shape
        roi=im[h//2-24:h//2+24,w//2-28:w//2+28]
        hits=roi[:,:,0]>=250
        through=roi[:,:,2]<230
        useful=hits&through
        actual=roi[:,:,1];expected=roi[:,:,2]
        if stage=='submerged':
            err=np.abs(actual[useful]-expected[useful])
            data[stage]=dict(hits=int(np.sum(hits)),tested=int(np.sum(useful)),medianActual=float(np.median(actual[useful])),
                             medianExpected=float(np.median(expected[useful])),maxErrorBytes=float(np.max(err)),
                             p95ErrorBytes=float(np.percentile(err,95)),withinOneByte=int(np.sum(err<=1)))
        else:
            data[stage]=dict(hits=int(np.sum(hits)),minActual=float(np.min(actual[hits])))
    (HERE/'submerged-transmission.json').write_text(json.dumps(data,indent=2)+'\n')
