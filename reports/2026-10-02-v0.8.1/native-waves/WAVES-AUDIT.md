# Fixed nonzero-wave first-visible-bed proof

This is a **qualified native PASS, not a new shader RED→GREEN**. The original first attempt remains [INCONCLUSIVE](first-inconclusive.log): its ideal pixel-centre geometry comparison rejected the raster-interpolated FS position before judging source transport. Its expanded production/observer shaders are byte-identical to the qualified attempt. No shader or transport tolerance was changed to obtain this PASS.

## Frozen inputs and scope

[Qualified log](qualified.log), [CSV](qualified/first-visible-bed.csv), [quad qualification](qualified/first-visible-bed-qualification.csv) and [mesh qualification](qualified/first-visible-bed-mesh.csv) are copied byte-for-byte from the original build artifacts. NVIDIA RTX 3080 Ti / GL4.6 / driver580.173.02; 129×129 native framebuffer; NEAREST C4/depth; public `WAVE_HEIGHT=0.12`, `SHORE_FOAM=0`; fixed phase1.25 and pixel65,48. The real VS/main uses an explicit one-metre ABC/ACD triangle grid, x[-8,8], z[-24,0], and a confirmed local two-metre column. C8/direct Sun is zero. The remote closed-box floor and its coherent bathymetry vary between2/6/8m; the qualified local water quad and first visible shelf remain unchanged.

## Independent CPU checks

All three uninstrumented C0 green-tag differences independently reproduce **0.09927815198898315**, within the declared physical range **[0.09845314936292449, 0.10009116617367718]**. Independent Snell/plane intersection gives first shelf travel **3.0555416720807984m** and unpolarized Fresnel **0.2842694957357829**, given the actual FS optical normal. Each returns kind1/confidence1, box0, and the independent first-source texel **(62,21)**. Accepted optical path3.0656449794769m lies within the camera-texel/R32F footprint interval[2.9696927605444,3.1638179178885]. Initial proxy seeds differ3.055523/9.448879/12.646093m; no forced hit, confidence or copied refraction marcher supplies the result.

The source C4 tag is present, while original-UV proxy C4 is unchanged. Tagged-versus-neutral reflection RGB difference is0 at the tested pixel. All **18 archived observation C0 images** (three modes × neutral/tag × three cases) exactly match their production images, and all three full-image repeat differences are0. The source/range checks are therefore nonvacuous, not merely geometry assertions or instrumentation-colour output.

An independent plane/barycentric raycast over all425 original-VS transform-feedback vertices reproduces all12 derivative-quad first-surface rows. Maximum FS-versus-first-mesh position error is **5.3615039874e-7m**; shared-edge coincident first hits are explicitly counted, not silently discarded. P/optical-normal/transmitted-ray/local-column remote-state delta is0; independent Snell discrepancy is at most7.0635807425e-8.

[Raster precision](qualified/raster-precision.txt) records `GL_SUBPIXEL_BITS=8`, a stated half-grid snapping envelope0.001953125px plus8×float32-epsilon×129=0.00012302398681641px. Maximum measured backprojection offset is0.0011518561428545px. The qualified reference ray is the actual FS backprojection, then checked against the *first* original-VS surface. This is the pinned-driver harness's declared geometry qualification, **not a universal OpenGL rounding or formal arithmetic-error proof**; colour/path/source bounds were not widened from observed output error.

## Provenance and limits

[FILE-SHA256.json](FILE-SHA256.json) inventories295 copied output/source files; [outputs-and-source.tgz](outputs-and-source.tgz) freezes those files and the inventory without modifying an older archive. Current source snapshot hashes match the producer's confirmed at-run hashes:

- Harness header: `4d3c252fbf5ebb60880f413b7ddaca7b040ad8cdc98ca295f3595f0c1e956dbf`.
- glcheck.cpp: `9cc28b88f398b27fd9dea89c8f65966bfafe7227b20581191ce3ac794dcacf4c`.
- Expanded production VS: `98e5c11d2e6d25d84cede59d24882e609a35334bb9724817929c43d4fa69e068`.
- Expanded production FS: `055a1f952efa920f99fe545255aaec68b49a08eba98c06e2e40b7fe5a1084bcd`.
- Qualified log: `2c786eac2f2899ef13b105e33a1eb53639a192946cda851ca42eca68e420eb0e`.
- Archive: `59b5e9bb65c4a60dc2739a341510c4633b904f7d4ab7e426e77acdee48d81a7b`.

The observer program is relinked for transform-feedback capture; its C0 equivalence to the unmodified production link is measured on these inputs. This audit copied/read files and performed CPU calculations only: no GL execution, game actions, world/configuration changes or production edits. It does **not** validate Sodium's actual mesh topology, the wave spectrum or physical correctness of the supplied optical normal, LINEAR nonzero-wave behavior, multiple phases/pixels, natural shoreline appearance, temporal stability, sunlight/cloud realism or Minecraft FPS. The overall realism goal remains open.
