"""Decode the retained atlas; choose quantitative raw-readback pairs, no edits."""
import json
import struct
import zlib
from water_coast_attribution_pack import OUT
import report


def paeth(a,b,c):
    p=a+b-c
    distances=(abs(p-a),abs(p-b),abs(p-c))
    return (a,b,c)[distances.index(min(distances))]


def atlas_point(x,y):
    # GL bottom-left pixel center: uvY=(1439-y+.5)/1440.
    # Top-half wrapped2x uv maps to texel floor(1439-2*y).
    return [2*x+1,1439-2*y]


def decode(raw, size):
    report.check_png_bytes(raw,size)
    channels = 3 if raw[25] == 2 else 4
    offset, chunks = 8, []
    while offset < len(raw):
        n=struct.unpack_from('>I',raw,offset)[0]
        if raw[offset+4:offset+8] == b'IDAT':
            chunks.append(raw[offset+8:offset+8+n])
        offset += n+12
    encoded=zlib.decompress(b''.join(chunks))
    width,height=size
    stride=width*channels
    pixels=bytearray(height*stride)
    for y in range(height):
        mode=encoded[y*(stride+1)]
        row=encoded[y*(stride+1)+1:(y+1)*(stride+1)]
        for x,value in enumerate(row):
            here=y*stride+x
            left=pixels[here-channels] if x>=channels else 0
            up=pixels[here-stride] if y else 0
            ul=pixels[here-stride-channels] if y and x>=channels else 0
            predictor=(0,left,up,(left+up)//2,paeth(left,up,ul))[mode]
            pixels[here]=(value+predictor)&255
    return pixels,channels


def analyze():
    path=OUT/'iris1440-run-v1/coast-day.png'
    pixels,channels=decode(path.read_bytes(),(2560,1440))
    def rgb(x,y):
        start=(y*2560+x)*channels
        return list(pixels[start:start+3])
    def record(x,y):
        return dict(panelPixel=[x,y], originalTextureApproxPixel=atlas_point(x,y),
            C0DisplayedRGB=rgb(x,y),knowledgeDisplayedRGB=rgb(x+1280,y),
            transmissionDisplayedRGB=rgb(x,y+720),reflectionDisplayedRGB=rgb(x+1280,y+720))
    def interior(x,y):
        return rgb(x+1280,y)==[0,255,255] and rgb(x+1280,y+720)==[255,0,255]
    luminance=lambda c:sum(a*b for a,b in zip(c,(.2126,.7152,.0722)))
    candidates=[]
    for y in range(330,620,3):
        for x in range(160,1100,3):
            if not interior(x,y):
                continue
            miss=rgb(x,y+720)
            if not (miss[0]<=10 and miss[1]==0 and miss[2]<=40):
                continue
            for shift in (-8,-4,4,8):
                other=x+shift
                if not interior(other,y):
                    continue
                hit=rgb(other,y+720)
                if not (hit[0]>=240 and hit[1]==255 and hit[2]<=40):
                    continue
                delta=luminance(rgb(other,y))-luminance(rgb(x,y))
                if delta>30:
                    candidates.append((delta,x,y,other))
    selected=[]
    for delta,x,y,other in sorted(candidates,reverse=True):
        if any((x-p['miss']['panelPixel'][0])**2+(y-p['miss']['panelPixel'][1])**2<40**2 for p in selected):
            continue
        selected.append(dict(displayLuminanceCodeDifference=delta,miss=record(x,y),hit=record(other,y)))
        if len(selected)==8:
            break
    assert len(selected)==8, 'Need eight distinct actual known/SSR-miss hit-proxy contrast pairs'
    receipt=dict(schema='aqualumen-coast-atlas-pair-selection-v1', pairs=selected,
        selection='known cyan + SSR miss magenta; proxy R<=10/G0 and opaque hit R>=240/G255; Fresnel blue<=40; display luminance difference>30 codes; horizontal separation4/8 panel pixels; pair centers>=40pixels apart',
        pixelMapping='ideal2x atlas texel mapping, not qualified exact binary32/final-sampler correspondence',
        units='PNG display codes, NOT linear radiance or energy',
        sameFrameAtlasPanels=True,selectedRawAndPNGSameFrameProven=False,
        cause='Correlation narrows the next causal probe to refraction receiver/proxy path, not yet a physical correctness verdict',
        solved=False,fullGoalAchieved=False)
    with (OUT/'atlas-pair-selection-v2.json').open('x') as f:
        json.dump(receipt,f,indent=2,sort_keys=True)
    print('pixels='+','.join(f'{p[0]}:{p[1]}' for pair in selected
        for p in (pair['miss']['originalTextureApproxPixel'],pair['hit']['originalTextureApproxPixel'])))
    print(json.dumps(selected,indent=2))


if __name__=='__main__':
    analyze()
