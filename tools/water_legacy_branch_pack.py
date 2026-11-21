"""Reversible TEST legacy failure ledger, not an optical fix or installation."""
import argparse
import json
from pathlib import Path
import water_gh_phase_pack as gh

OUTPUT = gh.ROOT / 'reports/2026-10-06-water-legacy-branch'
PINS = {0: '90c7d9dc1d98dfd45ff050f2f08e0bd516b756a1109dd19d738d969723da341d',
        45: 'b8bd19dff8c61b83311168e10eaa5704d2271ac805890404d4781cc316608069'}
MANIFEST = 'WATER-LEGACY-BRANCH.json'
PARENT = 'LEGACY-BRANCH-original/parent.zip'
VERSION = 2


def files(parent, call):
    if call not in ('full', 'base') or gh.sha(parent) not in PINS.values():
        raise ValueError('Unapproved parent or call')
    phase = next(k for k, v in PINS.items() if gh.sha(parent) == v)
    original = gh._archive(parent)
    result = dict(original)
    helper = original[gh.RESIDUAL]
    def add(source, anchor, name, body):
        return gh._one(source, anchor, anchor + gh._tag('WLB', name, body))
    helper = add(helper, b'vec4 WR_sources=vec4(0.0); // air-sky T, water R, opaque T, opaque R masses\n', 'GLOBALS', b'''
// TEST observation only: masks do NOT change original predicates or rays.
vec4 WLB_current[7];
vec4 WLB_saved[7];
int WLB_union=0,WLB_first=0,WLB_index=-2,WLB_failed=0;
int WLB_firstBit(int mask) {
    for (int bit=1;bit<=1024;bit*=2) if ((mask&bit)!=0) return bit;
    return 0;
}
void WLB_note(int mask,int node,vec3 transmitted,vec3 reflected,float facing,bool tir) {
    WLB_union|=mask;
    if (mask!=0) {
        WLB_failed+=1;
        if (WLB_first==0) {
            WLB_first=WLB_firstBit(mask);WLB_index=node;
            WLB_current[5]=vec4(transmitted,float(tir));
            WLB_current[6]=vec4(reflected,facing);
        }
    }
}
void WLB_save() {
    WLB_current[3]=WR_status;
    WLB_current[4]=vec4(float(WLB_union),float(WLB_first),float(WLB_index),float(16+WLB_failed));
    WLB_saved[0]=WLB_current[0];WLB_saved[1]=WLB_current[1];
    WLB_saved[2]=WLB_current[2];WLB_saved[3]=WLB_current[3];
    WLB_saved[4]=WLB_current[4];WLB_saved[5]=WLB_current[5];
    WLB_saved[6]=WLB_current[6];
}
''')
    helper = add(helper, b'    valid=valid && vertical>0.5 && meanProjected>1e-5;\n', 'INPUT', b'''
    WLB_current[0]=vec4(0.0);WLB_current[1]=vec4(0.0);
    WLB_current[2]=vec4(0.0);WLB_current[3]=vec4(0.0);
    WLB_current[4]=vec4(0.0);WLB_current[5]=vec4(0.0);WLB_current[6]=vec4(0.0);
    WLB_current[0]=vec4(meanNormal,float(eligible));
    WLB_current[1]=vec4(viewToEye,meanProjected);
    WLB_current[2]=vec4(WR_covariance,vertical);
    int WLB_mask=0;
    if (!finiteCovariance) WLB_mask|=1;
    if (!(covariance.x>=0.0 && covariance.z>=0.0)) WLB_mask|=2;
    if (!(remainder>=0.0)) WLB_mask|=4;
    if (!(rootX>0.0 || covariance.y==0.0)) WLB_mask|=8;
    if (!(vertical>0.5)) WLB_mask|=16;
    if (!(meanProjected>1e-5)) WLB_mask|=32;
    WLB_union=WLB_mask;WLB_first=WLB_firstBit(WLB_mask);
    WLB_index=WLB_mask!=0?-1:-2;WLB_failed=0;
''')
    helper = add(helper, b'        vec3 reflectedRay=reflect(-viewToEye,facet);\n', 'NODE', b'''
        int WLB_mask=0;
        if (!(facing>0.0)) WLB_mask|=64;
        if (!(reflectedRay.y<0.0)) WLB_mask|=128;
        if (!(tir || transmittedRay.y>0.0)) WLB_mask|=256;
''')
    helper = add(helper, b'                WR_sources.z+=weight*transmittance;\n', 'TRANSMITTED_RECEIVER', b'                WLB_mask|=512;\n')
    helper = add(helper, b'            WR_sources.w+=weight*reflectance;\n', 'REFLECTED_RECEIVER', b'            WLB_mask|=1024;\n')
    helper = add(helper, b'        WR_sources.y+=weight*reflectance;\n', 'NOTE',
                 b'        WLB_note(WLB_mask,3*x+z,transmittedRay,reflectedRay,facing,tir);\n')
    result[gh.RESIDUAL] = helper
    sun = add(original[gh.SUN], b'vec4 WGP_readLegacyStatus();\n', 'PROTOTYPE', b'void WLB_save();\n')
    result[gh.SUN] = add(sun, f'    WGP_{call}WR=WGP_readLegacyStatus();\n'.encode(), 'SAVE', b'    WLB_save();\n')
    water = add(original[gh.WATER], b'void main() {\n', 'RESET', b'''    WLB_saved[0]=vec4(0.0);WLB_saved[1]=vec4(0.0);WLB_saved[2]=vec4(0.0);
    WLB_saved[3]=vec4(0.0);WLB_saved[4]=vec4(0.0);WLB_saved[5]=vec4(0.0);WLB_saved[6]=vec4(0.0);
''')
    water = add(water, b'// AQUALUMEN_GH_OBSERVE_END:STORE\n', 'STORE', b'''
    // Native-only alternate export retains the previously written TES record.
    // It changes only an observation slot, never geometry or physical C0.
    vec4 WLB_tes=gl_FragData[4];
    gl_FragData[1]=WLB_saved[0];
    gl_FragData[2]=WLB_saved[1];
    gl_FragData[3]=WLB_saved[2];
    gl_FragData[4]=WLB_saved[3];
    gl_FragData[5]=WLB_saved[4];
    gl_FragData[6]=WLB_saved[5];
    gl_FragData[7]=WLB_saved[6];
#ifdef WLB_NATIVE_EXPORT_TES
    gl_FragData[1]=WLB_tes;
#endif
''')
    result[gh.WATER] = water
    for n in (gh.RESIDUAL, gh.SUN, gh.WATER):
        if gh._erase_tags(result[n], 'WLB') != original[n]:
            raise ValueError('Exact source recovery differs')
    meta = dict(schema=f'aqualumen-water-legacy-branch-v{VERSION}', phase=phase,
        selectedCall=call, parentSha256=gh.sha(parent), parentMember=PARENT,
        changedExistingMembers=[gh.RESIDUAL, gh.SUN, gh.WATER],
        layout=['normal.xyz/eligible','view.xyz/meanProjected','covariance.xyz/vertical',
                'WR_status','unionMask/firstBit/firstNode/16+failedNodes',
                'firstTransmitted.xyz/TIR','firstReflected.xyz/facing'],
        failureBits={'1':'finiteCovariance','2':'nonnegativeDiagonal','4':'SchurRemainder',
                     '8':'rankZeroCross','16':'vertical','32':'meanProjected','64':'facing',
                     '128':'reflectedHemisphere','256':'transmittedHemisphere',
                     '512':'transmittedOpaqueReceiver','1024':'reflectedOpaqueReceiver'},
        firstNodeConvention='-2 none; -1 prerequisites; 0..8 x*3+z',
        sourceRecoveryExact=True, onlyObservationAdded=True,
        finalHistoricalLayoutNoLongerAuthoritative=True,
        geometryShaderFilesUnchanged=True, sourceUnitsUnchanged=True,
        CPUOnly=True, GLAccepted=False, IrisAccepted=False,
        physicalAccepted=False, visualAccepted=False, shippingAccepted=False)
    result[PARENT] = parent
    result[MANIFEST] = (json.dumps(meta, indent=2, sort_keys=True) + '\n').encode()
    result['LEGACY-BRANCH-expanded.fsh'] = gh._expand(result, gh.WATER)
    return result, meta


def build(parent, call, output):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Destination exists')
    if output.resolve() != output or not (output.is_relative_to(OUTPUT) or output.is_relative_to(Path('/tmp'))):
        raise ValueError('Output outside new TEST subtree or /tmp')
    data, meta = files(gh._read(parent), call)
    if output.name != f'Aqualumen-ShoreProbe-world-legacy-branch-{meta["phase"]}-{call}-v{VERSION}.zip':
        raise ValueError('Dedicated filename required')
    gh._publish(gh._zip(data), output)
    return dict(packSha256=gh.sha(gh._read(output)), **meta)


def recover(candidate):
    data = gh._archive(gh._read(candidate))
    parent = data[PARENT]
    expected, _ = files(parent, json.loads(data[MANIFEST])['selectedCall'])
    if data != expected:
        raise ValueError('Source or metadata tamper')
    return parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent', type=Path, required=True)
    p.add_argument('--call', choices=('full','base'), required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args()
    print(json.dumps(build(a.parent,a.call,a.output), sort_keys=True))


if __name__ == '__main__':
    main()
