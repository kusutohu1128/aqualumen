# Main-cap TEST old/stable packs — CPU handoff

Public API: `build_pack(root,destination,mode='stable',observe='reasons')`.
CLI: `python3 tools/water_snell_main_pack.py NEW.zip --mode old|stable
--observe reasons|inputs`. Destinations are never overwritten; production
shaders/dist and older report trees are rejected. Only this new report packet
was written. No GL, game, world, shipping shader or old report was modified.

The four exported ZIPs preserve the frozen reason-parent pack chain. `old`
with `reasons` preserves every inherited shader byte. `stable` changes four
inverse-node spans: facet/support, transmitted ray, Jacobian and transmission.
The exact stable function is pinned to original `4338e677...4330e27`; only its
extension guard block is removed in the adapted include. The FP64 directive is
hoisted immediately after the water FS version, before all declarations. The
original node module is archived; restoring its extension block recovers its
exact bytes. Geometry, FINAL, target generation, source units and covariance
remain unchanged.

Existing axis precheck, reflection formula, original reconstruction EPS and
`k*target` comparison, ray length/up checks, reflected-world hemisphere,
refraction/reflection receivers, full/base admission and whole-source fallback
remain byte-preserved. Status0 and status-1 both reject the complete replacement;
there is no support-zero integration or survivor renormalization. Stable reason2
now reflects the new inverse-node status rejection, not proof that the original
float discriminant predicate failed. The old nine-node wrapper can still exclude
a supported critical node before the new cap loop; a pure-node numerical RED is
not a whole-main RED or fix.

## Passive inputs variant

Eight removable helper assignment blocks record actual wrapper entry/raw mean,
raw view, covariance, and the first failed generated target. Source-recovery
tests recover each same-variant reason helper exactly. Replacing input STORE
with the original reason STORE recovers each same-variant reason water FS.
Removing either STORE recovers the archived `SNELL-MAIN-physical.fsh`.

| MRT | Inputs policy |
| --- | --- |
| C9 | raw mean xyz, helperCalled |
| C10 | raw view xyz, requested |
| C11 | helper covariance xyz, original main production flags |
| C12 | first failed raw generated target xyz, encoded reason/node |

C12.w is integer `nodeIndex+64*firstReason`, nodeIndex1..48 and reason1..9;
zero means no captured loop failure. The first-reason recorder executes before
the unchanged common failure, so target/reason/index are same-draw witnesses.
They do not describe all48 nodes. Helper-not-called/guard0 defaults are zero;
pre/post-loop fallback or old full/base exclusion can have no captured target.
helperCalled/requested/flags do not prove application. C12 is **not TES**. FINAL
bytes remain parent-exact; its inherited diagnostic legends are not authoritative
for the input atlas. CPU source recovery is not actual GL C0/depth neutrality.

## Incremental evidence and limits

`01` missing-builder API RED → `02` old exact GREEN → `03/04` stable seam
RED/GREEN → `05/06` inputs CLI RED/GREEN. `07/08` finish with **5 public tests
PASS**, including negative-policy preservation and non-overwrite behavior.
These are packaging/source contracts, not new main-stage numerical, native,
Iris, visual, physical, motion or shipping acceptance.

Root owns installation aliases
`Aqualumen-ShoreProbe-world-snell-main-{old|stable}-{reasons|inputs}-v1.zip` to
meet the TEST Mod's filename guard. These are same-ZIP-byte aliases, not altered
exports; their installation/runtime state is not attested by this CPU worker.

All owned builder/test/report writes stop after the receipt is generated.
