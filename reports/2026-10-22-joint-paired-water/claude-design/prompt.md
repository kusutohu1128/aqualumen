# Claude independent design for paired water diagnostic

Read AGENTS.md and .audit/paired-water-2026-10-22.contract.md first. User authorized joint development with Claude. You own one readonly design candidate now, not code yet. Parent alone will integrate. Only Read/Glob/Grep are available. No writes, commands, game/GPU/benchmarks, further agents or credential reads.

Produce a SHORT concrete design in Japanese or English, max about1000 words. Limit exploration to the files below and directly necessary callees, approximately12 Read/Grep calls. Do not re-investigate all historical packets. The prior Claude status review is in reports/2026-10-22-claude-status-review/CLAUDE-REPORT.md if needed, but this task is narrower.

Compare two structurally distinct candidates:
1. Water C12 passive MRT reflection route plus an actual same-FINAL-invocation raw C12 / final framebuffer observer.
2. Same-frame explicit-address beauty/classification atlas in FINAL.

Read current shaders/gbuffers_water.fsh, lib/water_receiver.glsl, lib/uniforms.glsl, lib/ripples.glsl, final.fsh. Existing tools/atlas-joint-probe/dev/aqualumen/atlasjoint/{JointObserver,OutputSnapshot}.java and mixin/JointMixin.java show before/after FINAL, but obsolete hardcoded layout must not be installed unchanged. tools/display_water_runtime.py is the guarded parent-owned lifecycle.

Class schema: RGBA32F (route,Fresnel,travel,waterMask), routes0notwater,1SSR,2world-ready,3known-unready,4unknown,5producer-unavailable. It must classify the ACTUAL original reflection path without a second ray trace or changing beauty. Shader copies only: freeze frameTimeCounter17.0 and disable interaction ripple sampling in both control and diagnostic. Root shader files/defaults stay untouched. Detect source-shape mismatches strictly.

For candidate1, FINAL needs an actual bound C12 sampler to avoid choosing the wrong flip texture. Proposed optional diagnostic preview selector int aqualumenPairedView, verified0 at beauty capture, keeps the C12 sampler active without mathematical zero tricks. Assess pinned Iris feasibility and uniform defaults. Prefer a clearly registered uniform via TEST shaders.properties if possible. Explicitly bound framebuffer storage and color encoding/state restoration are required.

Return each candidate's caller usage and signatures/types, interface responsibilities, failure outcomes, minimal parent/Claude file ownership, native and real-Minecraft verification criteria. Select a base and explain what would falsify it. Do not implement a general framework or require modifications to the normal pack. The output is a design contract, not a claim the view is fixed.
