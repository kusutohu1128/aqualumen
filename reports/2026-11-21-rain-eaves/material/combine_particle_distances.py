"""Require the independently positioned camera to populate distance bands missing in the close view."""
import argparse
import json
from pathlib import Path

def merge(near,far,destination):
    inputs=[json.loads((d/"particle-depth.json").read_text()) for d in (near,far)]
    result={}
    for phase in ("warm_rain","soul_rain","lamp_back"):
        stages=[j["stages"][phase] for j in inputs]
        # The radius limit is tested from the distant camera; the close camera supplies the high-energy interior.
        inner=stages[0]["sourceDistanceBands"][0]
        outer=stages[1]["sourceDistanceBands"][-1]
        out={"closeSamples":stages[0]["samples"],"farSamples":stages[1]["samples"],
             "inner":inner,"outer":outer,"brightUpperRightInOrdinaryView":stages[0]["upperRightBrightestLocalDecile"],
             "positionErrorsP99Metres":[s["geometricRayErrorMetresP50P95P99"][2] for s in stages],
             "tracedVsSurveyedLampP99Metres":[s["tracedSourceVsNominalMetresP50P95P99"][2] for s in stages if s["tracedSamples"]]}
        out["checks"]={"nearLit":inner["samples"]>500 and inner["directEnergyP50P90P99"][1]>.02,
            "farRangeActuallyObserved":outer["samples"]>500,
            "farLocalLightVanished":outer["samples"]>500 and outer["directEnergyP50P90P99"][2]<.001,
            "bothCameraRaysAgree":max(out["positionErrorsP99Metres"])<.25,
            "warmOrSoulSourceLocated":max(out["tracedVsSurveyedLampP99Metres"])<.25}
        result[phase]=out
    controls={state:all(j["checks"][state] for j in inputs) for state in ("clear_sky_no_particles","unlit_rain_has_no_direct_lamp")}
    ok=all(controls.values()) and all(all(s["checks"].values()) for s in result.values())
    evidence={"fixedWorld":"A single surveyed hanging lamp, photographed from two actual Minecraft camera positions.",
              "runs":[near.name,far.name],"controls":controls,"states":result,"passed":ok}
    destination.write_text(json.dumps(evidence,indent=2)+"\n")
    return ok
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("near","far","destination"):p.add_argument(name,type=Path)
    a=p.parse_args()
    raise SystemExit(not merge(a.near,a.far,a.destination))
