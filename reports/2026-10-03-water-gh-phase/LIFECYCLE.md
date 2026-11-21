# Root-owned runtime lifecycle

The ordinary client was freshly inspected with F2 at22:43:39 JST2026-10-03:
window62914567,1600x900, paused ordinary singleplayer. Root selected the visible
Save and Quit button; latest.log records all dimensions saved at22:44:14.
Fresh F2 at22:44:16 established the title screen before selecting its Quit button.
The SAME owned exec session8418 then returned exit0; `pgrep -x java` returned
exit1/no matches. No native GL had been executed at that point.

Current ordinary options, Iris and benchmark configuration were copied to the
private new cache `/home/kusutohu/.cache/aqualumen-gh-phase.BN6hPp` after the clean
exit. Their SHA256 values respectively are:

- `02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`
- `6db579ada1e7e64eb249094fff355c148493629960e57fd899b33801d193f78b`
- `45a4c9b0269ec47b3a72fa73647e92702b6012be10f273a60d37f69c9ca148d1`

A whole ordinary save copy exists privately for comparison only. It must never
be restored over the live save. Ordinary reopen/save naturally advances saves;
do not describe a later reopened save as byte-identical to this snapshot.

An initial read-only Prism `--help` check failed because DISPLAY was absent;
repeating with DISPLAY=:1 returned exit0 and verified its standard --launch
interface. This was not a shader or game launch failure. No account/launcher
output or private save copy is included in this report packet.

Native and TEST runs, if undertaken, will be recorded below before normal
restoration. This file does not yet claim a TEST launch, GPU result or return.
