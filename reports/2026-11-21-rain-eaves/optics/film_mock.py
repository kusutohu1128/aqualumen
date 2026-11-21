#!/usr/bin/env python3
"""Build throw-away pack trees under /tmp for exercising tools/rain-film-probe.h (the repository is only read).

  film_mock.py mutate OUT NAME   copy release/shaders to OUT/shaders and apply ONE named exact-substring mutation to the
                                 parent's real files => the probe must FAIL (negative control).
  film_mock.py list              print the mutation names.
OUT must not exist (never overwrites)."""
import shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
REL = ROOT / "release/shaders"
F, M, L = "lib/dielectric_film.glsl", "lib/rain_material.glsl", "lib/local_lighting.glsl"

# name -> (file, exact old substring, new substring, what it models)
MUTATIONS = {
    "fresnel_f0_0.04":      (F, "0.0204+0.9796*pow", "0.04+0.96*pow", "wrong normal-incidence F0"),
    "fresnel_view_normal":  (F, "filmFresnel(dot(view,h))", "filmFresnel(nv)", "Fresnel on n.v instead of the half vector"),
    "no_masking":           (F, "float smith=0.5/max(nl*sqrt(a2+(1.0-a2)*nv*nv)+nv*sqrt(a2+(1.0-a2)*nl*nl),smithFloor);", "float smith=0.25;", "masking/shadowing removed"),
    "roughness_squared":    (F, "pow(roughness,4.0)", "pow(roughness,2.0)", "perceptual roughness mapped to alpha^1 instead of alpha^2"),
    "extent_ignored":       (F, "+emitterSlope2,0.00012", "+0.0*emitterSlope2,0.00012", "finite emitter extent ignored"),
    "hemisphere_missing":   (F, "    if(nl<=0.0 || nv<=0.0) return 0.0;\n", "", "no below-hemisphere rejection"),
    "times_pi":             (F, "return a2*smith*filmFresnel(dot(view,h))/(den*den);", "return 3.14159265*a2*smith*filmFresnel(dot(view,h))/(den*den);", "normalization off by pi"),
    "ndf_wrong_width":      (F, "float den=(1.0-nh*nh)+nh*nh*a2;", "float den=(1.0-nh*nh)+nh*nh*a2*2.0;", "GGX denominator wrong"),
    "wet_ratio_ignored":    (F, "max(scatteringRatio,0.0001)", "1.0", "scattering ratio ignored (no darkening)"),
    "wet_identity_broken":  (F, "vec3 numerator=2.0*r*max(scatteringRatio,0.0001);", "vec3 numerator=2.2*r*max(scatteringRatio,0.0001);", "ratio=1 is not the identity"),
    "wet_inverted":         (F, "vec3 numerator=2.0*r*max(scatteringRatio,0.0001);", "vec3 numerator=2.0*r/max(scatteringRatio,0.0001);", "wet substrate brighter than dry"),
    "wet_white_darkens":    (F, "vec3 r=clamp(dry,0.0,1.0), lost=1.0-r;", "vec3 r=clamp(dry,0.0,0.98), lost=1.0-r;", "white endpoint not preserved"),
    "material_ineligible_covered": (M, "return vec3(1.0,1.0,0.0);", "return vec3(1.0,1.0,0.05);", "non-eligible ids get film coverage"),
    "material_no_darkening": (M, "if(id==10600) return vec3(.72,.22,.91);", "if(id==10600) return vec3(1.0,.22,.91);", "eligible material with ratio 1"),
    "material_ineligible_ratio": (M, "return vec3(1.0,1.0,0.0);", "return vec3(0.9,1.0,0.0);", "non-eligible ids carry a darkening ratio"),
    "lamp_no_coverage":     (L, "    reflectedLamp*=coverage;\n", "", "grid-edge fade missing on the wet term"),
    "lamp_ignores_visibility": (L, "reflectedLamp+=energy*(nl*brdf);", "reflectedLamp+=(energy/max(vis,vec3(0.001)))*(nl*brdf);", "wet reflection not occluded"),
    "lamp_no_cosine":       (L, "reflectedLamp+=energy*(nl*brdf);", "reflectedLamp+=energy*brdf;", "receiver cosine dropped"),
    "lamp_extent_missing":  (L, "float emitterSlope2=radius*radius/(4.0*max(d2,0.1));", "float emitterSlope2=0.0;", "lamp extent not passed"),
    "lamp_view_is_light":   (L, ":filmDirectBRDF(normal,view,l,roughness,emitterSlope2);", ":filmDirectBRDF(normal,l,l,roughness,emitterSlope2);", "viewer direction lost"),
    "lamp_film_false_leaks": (L, "if(water || film) {", "if(water || film || true) {", "film=false still writes reflectedLamp"),
    "lamp_film_changes_diffuse": (L, "            total+=diffuse;\n        }\n        if(water || film) {", "            total+=film?diffuse*0.5:diffuse;\n        }\n        if(water || film) {", "film flag perturbs the ordinary diffuse return"),
    "lamp_wrong_slope_scale": (L, "float emitterSlope2=radius*radius/(4.0*max(d2,0.1));", "float emitterSlope2=radius*radius/(max(d2,0.1));", "extent slope^2 off by 4"),
}

def build(out: Path, name: str):
    if out.exists(): sys.exit(f"refusing to overwrite {out}")
    shutil.copytree(REL, out / "shaders")
    f, old, new, _ = MUTATIONS[name]
    p = out / "shaders" / f
    t = p.read_text()
    if t.count(old) != 1: sys.exit(f"mutation {name}: expected exactly one occurrence of the target text in {f}, found {t.count(old)}")
    p.write_text(t.replace(old, new))
    return out / "shaders"

if __name__ == "__main__":
    if sys.argv[1] == "list":
        for k, v in MUTATIONS.items(): print(k, "|", v[0], "|", v[3])
    elif sys.argv[1] == "mutate":
        print(build(Path(sys.argv[2]), sys.argv[3]))
    else:
        sys.exit(__doc__)
