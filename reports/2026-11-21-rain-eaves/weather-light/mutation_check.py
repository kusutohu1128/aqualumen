#!/usr/bin/python3
"""Negative controls: each mutant of the staging shaders must make the probe FAIL the named checks.
Writes only below build/weather-light-staging/mutants/ and mutation.json next to this script."""
import json, shutil, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
repo = here.parents[2]
st = repo / 'build/weather-light-staging'
probe = st / 'weather_light_probe'
base = st / 'baseline-rc3/shaders'
M = [
 ('orange_hardwired', 'gbuffers_weather.fsh',
  'int traced;\n    incident+=weatherLampLight(position,ray,lightmap.x,liquid,traced);',
  'int traced;\n    incident+=weatherLampLight(position,ray,lightmap.x,liquid,traced)+vec3(1.0,0.56,0.25)*pow(lightmap.x,3.0)*2.0;',
  ['lamp.off_torch_is_dark_and_never_orange', 'fallback.unsupported_light_is_weak_and_not_orange', 'lamp.stone_between_receiver_and_lamp_blocks_it']),
 ('no_source_visibility', 'lib/weather_light.glsl',
  'vec3 vis=lampVisibility(p+0.02*l,lamp.xyz,l,radius,carried,occluders);', 'vec3 vis=vec3(1.0);',
  ['lamp.stone_between_receiver_and_lamp_blocks_it', 'lamp.stained_glass_tints_per_channel', 'carried.distance_wall_and_removal']),
 ('local_times_sun_visibility', 'gbuffers_weather.fsh',
  'incident+=weatherLampLight(position,ray,lightmap.x,liquid,traced);', 'incident+=weatherLampLight(position,ray,lightmap.x,liquid,traced)*shadowVisibility(position,sun)*access;',
  ['daylight.local_energy_not_multiplied_by_sun_visibility_or_sky_access']),
 ('lambert_cosine_on_sun', 'gbuffers_weather.fsh',
  '(smoothstep(0.0,0.85,lightmap.y)*horizon', '(max(sun.y,0.0)*smoothstep(0.0,0.85,lightmap.y)*horizon',
  ['daylight.sun_matches_cpu_obeys_terrain_and_cloud_shadow_and_sky_term_unchanged']),
 ('sun_ignores_terrain_shadow', 'gbuffers_weather.fsh',
  '*shadowVisibility(position,sun)\n', '\n',
  ['daylight.sun_matches_cpu_obeys_terrain_and_cloud_shadow_and_sky_term_unchanged']),
 ('isotropic_phase', 'lib/weather_light.glsl',
  'return mix(weatherSnowPhase(clamp(mu,-1.0,1.0)),weatherRainPhase(clamp(mu,-1.0,1.0)),liquid);', 'return 1.0/(4.0*PI);',
  ['phase.rain_forward_lobe_vs_snow_diffuse', 'angle.rain_snow_mixture_matches_cpu_and_forward_exceeds_back']),
 ('unnormalized_phase', 'lib/weather_light.glsl',
  'return (1.0-g*g)/(4.0*PI*d*sqrt(d));', 'return (1.0-g*g)/(4.0*d*sqrt(d));',
  ['phase.normalized_and_matches_independent_cpu']),
 ('every_lamp_warm', 'lib/weather_light.glsl',
  'vec3 energy=lampColor(kind)*(', 'vec3 energy=vec3(1.0,0.49,0.19)*(',
  ['lamp.palette_kind_colour_and_strength_vs_cpu_model']),
 ('backward_angle_convention', 'lib/weather_light.glsl',
  'total+=energy*(PI*weatherAlbedo*weatherPhase(dot(ray,l),liquid));', 'total+=energy*(PI*weatherAlbedo*weatherPhase(-dot(ray,l),liquid));',
  ['angle.rain_snow_mixture_matches_cpu_and_forward_exceeds_back']),
 ('no_range_falloff', 'lib/weather_light.glsl',
  'float falloff=1.0-smoothstep(0.7*lampRange,lampRange,d);\n        float radius', 'float falloff=1.0;\n        float radius',
  ['distance.regularized_falloff_range_cutoff_and_monotone']),
 ('coverage_changed', 'gbuffers_weather.fsh',
  'if(coverage<0.004) discard;', 'coverage*=0.9;\n    if(coverage<0.004) discard;',
  ['coverage.alpha_and_discard_identical_to_rc3']),
 ('unbounded_sources', 'lib/weather_light.glsl',
  '#define WEATHER_LIGHT_SOURCES 4', '#define WEATHER_LIGHT_SOURCES 12',
  ['work.traced_sources_bounded_and_output_soft_limited']),
]
out = []
for name, rel, old, new, expect in M:
    dst = st / 'mutants' / name
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(st / 'pack/shaders', dst / 'shaders')
    f = dst / 'shaders' / rel
    text = f.read_text()
    if text.count(old) != 1: sys.exit(f'{name}: pattern found {text.count(old)}x')
    f.write_text(text.replace(old, new))
    r = subprocess.run([str(probe), str(dst / 'shaders'), str(base), str(dst / 'result.json')], capture_output=True, text=True)
    failed = [l.split()[1] for l in r.stdout.splitlines() if l.startswith('FAIL')]
    caught = [e for e in expect if e in failed]
    out.append({'mutant': name, 'file': rel, 'exit': r.returncode, 'failed_checks': failed, 'expected_to_fail': expect, 'all_expected_caught': len(caught) == len(expect)})
    print(f"{name:28s} exit={r.returncode} caught={len(caught)}/{len(expect)} failed={len(failed)}")
(here / 'mutation.json').write_text(json.dumps({'all_mutants_caught': all(o['all_expected_caught'] and o['exit'] != 0 for o in out), 'mutants': out}, indent=1) + '\n')
sys.exit(0 if all(o['all_expected_caught'] and o['exit'] != 0 for o in out) else 1)
