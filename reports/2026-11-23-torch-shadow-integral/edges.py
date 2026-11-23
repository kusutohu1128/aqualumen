"""Direct clipping of each projected cuboid edge, with a pole outside its shadow."""
def direct(text, directory):
    start=text.index("float boxSourceVisibility(")
    stop=text.index("// The two masks",start)
    single=text[start:stop]
    single=single.replace("bool centreInside=true;", "bool hasPole=false; vec2 pole=vec2(0.);")
    single=single.replace("if(abs(d)<1e-7) d=1e-7;\n        centreInside=centreInside && d>0.;",
                          "if(!hasPole) {pole=-n;hasPole=true;}")
    single=single.replace("float swept=d*(span.y-span.x);\n            integral+=swept-atan(swept,d*d+span.x*span.y);",
                          """vec2 foot=-d*n-pole;
            vec2 a=foot+span.x*tangent, b=foot+span.y*tangent;
            float chord=span.y-span.x;
            integral+=d*chord-2.*atan((d+dot(pole,n))*chord,dot(a,b));""")
    single=single.replace("(centreInside?0.:1.)-integral", "(hasPole?1.:0.)-integral")
    assert "centreInside" not in single
    text=text[:start]+single+text[stop:]
    start=text.index("void diskPlane(")
    stop=text.index("float oneBlocker(",start)
    solver=(directory/"chords.glsl").read_text().split("float boxSourceVisibility")[0]
    solver=solver.replace("dot(h.xy,tangent)", "dot(sum2<2.?sumNormal:-diff,tangent)")
    solver+="""
float intersectionVisibility(vec3 lo,vec3 hi,vec3 secondLo,vec3 secondHi,vec3 delta,vec3 u,vec3 v) {
    vec3 planes[24];
    int count=0;
    boxPlanes(lo,hi,delta,u,v,planes,count);
    boxPlanes(secondLo,secondHi,delta,u,v,planes,count);
    vec2 unused;
    return diskVisibility(planes,0,count,unused);
}

"""
    return (text[:start]+solver+text[stop:]).replace("shadowPlanes(","boxPlanes(")


def caps(text,directory):
    text=direct(text,directory)
    start=text.index("float boxSourceVisibility(")
    stop=text.index("// The two masks",start)
    single=text[start:stop].replace("boxSourceVisibility(","projectBox(").replace(
        "out vec2 witness)","out vec2 witness,out vec3 cut)")
    single=single.replace("float nearest=1.;","cut=vec3(0.,0.,2.);\n    float nearest=1.;")
    single=single.replace("if(!hasPole) {pole=-n;hasPole=true;}",
                          "if(!hasPole) {pole=-n;cut=vec3(n,d);hasPole=true;} else cut.z=2.;")
    wrapper="""float boxSourceVisibility(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,out vec2 witness) {
    vec3 cut;
    return projectBox(lo,hi,delta,u,v,witness,cut);
}
"""
    text=text[:start]+single+wrapper+text[stop:]
    start=text.index("float oneBlocker(")
    stop=text.index("float twoBlockers(",start)
    one=text[start:stop].replace("oneBlocker(","readBlocker(").replace(
        "out vec2 witness)","out vec2 witness,out vec3 cut)").replace(
        "    witness=vec2(0.);","    cut=vec3(0.,0.,2.);witness=vec2(0.);").replace(
        "boxSourceVisibility(lo,hi,delta,u,v,witness)","projectBox(lo,hi,delta,u,v,witness,cut)")
    wrapper="""float oneBlocker(vec3 lo,vec3 hi,vec3 delta,vec3 u,vec3 v,vec3 extent,out vec2 witness) {
    vec3 cut;
    return readBlocker(lo,hi,delta,u,v,extent,witness,cut);
}
"""
    text=text[:start]+one+wrapper+(directory/"caps.glsl").read_text()+text[stop:]
    text=text.replace("vec2 w1,w2;","vec2 w1,w2; vec3 cutA,cutB;").replace(
        "oneBlocker(lo,hi,delta,u,v,extent,w1)","readBlocker(lo,hi,delta,u,v,extent,w1,cutA)").replace(
        "oneBlocker(secondLo,secondHi,delta,u,v,extent,w2)","readBlocker(secondLo,secondHi,delta,u,v,extent,w2,cutB)")
    text=text.replace("    float intersection=intersectionVisibility",
            "    if(cutA.z<1. && cutB.z<1.) return twoCaps(cutA,cutB,first,second);\n    float intersection=intersectionVisibility")
    return text


def mask(text,directory):
    s=caps(text,directory)
    s=s.replace("out vec3 cut)","out vec3 cut,out int mask)")
    s=s.replace("cut=vec3(0.,0.,2.);","cut=vec3(0.,0.,2.);mask=0;")
    s=s.replace("if(!hasPole) {pole=-n;cut=vec3(n,d);hasPole=true;}", "mask|=1<<edge;\n        if(!hasPole) {pole=-n;cut=vec3(n,d);hasPole=true;}")
    s=s.replace("vec3 cut;","vec3 cut; int mask;").replace(",witness,cut);",",witness,cut,mask);")
    s=s.replace("vec3 cutA,cutB;","vec3 cutA,cutB; int maskA,maskB;")
    s=s.replace(",w1,cutA);",",w1,cutA,maskA);").replace(",w2,cutB);",",w2,cutB,maskB);")
    s=s.replace("float intersection=intersectionVisibility(lo,hi,secondLo,secondHi,delta,u,v);",
        """vec2 outside=dot(w1,w1)<dot(w2,w2)?w1:w2;
    if(dot(outside,outside)<1e-18) return min(first,second);
    float intersection=maskedIntersection(maskA|(maskB<<15),lo,hi,secondLo,secondHi,delta,u,v,normalize(outside));""")
    begin=s.index("void keepDiskPlane(")
    end=s.index("float readBlocker(",begin)
    animalPlanes=s[begin:s.index("float diskVisibility(",begin)] if "bool openArc(" in s else ""
    return s[:begin]+animalPlanes+(directory/"mask.glsl").read_text()+s[end:]
