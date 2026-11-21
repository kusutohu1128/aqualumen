# Coupled normal beauty comparison v92

Both actual Minecraft runs completed and were archived, with NVIDIA renderer,
active Iris pack, matching installed ZIP hashes and owned launcher exit 0.
Candidate request: `6800279f-8216-4398-aad2-673013111011`.
Control request: `87ae4e18-81d2-427f-9344-0aff8b36872c`.

The ZIP entry sets match exactly. The only payload difference is the explicit
`AQUALUMEN_INTERFACE_NORMAL_COMPARISON` definition in `gbuffers_water.fsh`;
removing that definition makes all payloads identical, including composite stages.

Both near principal images were visually inspected. The compressed/folded sky
rim and dark polygonal exterior persist in the candidate. The apparent window
extent differs substantially, but the wave time was not matched between launches;
do not attribute that extent difference or a quality improvement to the correction.
The geometric-side repair proven by v91 is insufficient to establish visual
resolution. Keep it opt-in, not enabled in the ordinary pack.

| Actual mean FPS | Near | Moving |
| --- | ---: | ---: |
| Candidate | 2.180 | 2.284 |
| Control | 2.077 | 2.197 |

One sequential run per role, 1600x800, five-second warmup and twenty-second sample.
These timings are unusable and are not a statistically established speedup.
No JFR was active. Temporal visual acceptance and current Sun-size acceptance
remain open. Next investigate the reflected exterior's source readiness and
sky-window sampling independently of geometric-side admission.

Normal configurations, Mods and ordinary save hashes matched after restoration;
no save rollback was performed. The client exited normally.
