#!/usr/bin/python3
"""Merge evidence.json, package.json, mutation.json and compile-only.log into a compact status.json."""
import json, time
from pathlib import Path
here = Path(__file__).resolve().parent
ev = json.loads((here / 'evidence.json').read_text()); pk = json.loads((here / 'package.json').read_text()); mu = json.loads((here / 'mutation.json').read_text())
log = (here / 'compile-only.log').read_text()
lines = log.splitlines(); compiled = sum(l.startswith('PASS ') and 'compile/link only' not in l for l in lines); cfail = sum(l.startswith('FAIL') for l in lines) + (0 if 'PASS gbuffers_weather' in lines else 1)
t = {r['name']: r['detail'] for r in ev['results']}
status = {
 'task': 'weather-light-staging', 'state': 'complete' if ev['failed'] == 0 and pk['ok'] and mu['all_mutants_caught'] and cfail == 0 else 'failed',
 'finished': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
 'minecraft_started': False, 'gpu_lock': 'not taken: sub-second GPU work (compile + 1-pixel draws); no overlap with the take-5 1440 benchmark (finished 05:04:17 JST, before any GPU use here)',
 'renderer': ev['renderer'], 'gl_version': ev['gl_version'],
 'archive': pk['staging_zip'], 'archive_sha256': pk['staging_zip_sha256'], 'base_sha256': pk['rc3_sha256'],
 'changed': pk['changed'], 'added': pk['added'], 'vertex_shader_unchanged': pk['unchanged_vertex_and_support_files']['shaders/gbuffers_weather.vsh'],
 'file_sha256': pk['file_sha256'],
 'probe': {'checks': ev['checks'], 'failed': ev['failed'], 'weather_fsh_sha256': ev['weather_fsh_sha256'], 'weather_light_glsl_sha256': ev['weather_light_glsl_sha256']},
 'mutation': {'mutants': len(mu['mutants']), 'all_caught': mu['all_mutants_caught']},
 'compile_only': {'programs_linked': compiled, 'failed': cfail},
 'old_vs_new': t.get('compare.far_streaks_dim_and_soul_not_orange'),
 'timing_gpu_harness_ms_per_1280x720_full_coverage_quad_[rc3,staging]': t.get('timing.gpu_harness_worst_case_quad'),
 'reproduce': 'reports/2026-11-21-rain-eaves/weather-light/reproduce.sh',
}
(here / 'status.json').write_text(json.dumps(status, indent=1) + '\n')
print(status['state'], ev['checks'], 'checks', ev['failed'], 'failed;', len(mu['mutants']), 'mutants caught=', mu['all_mutants_caught'], '; compile-only', compiled, 'ok', cfail, 'failed')
