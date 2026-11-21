# Six-sigma glare candidate

Full NVIDIA native regressions and 13 shader program pairs pass in
`../native-check-six-sigma.log`. Independent 65/450/900 convolution checks also
bound the high-HDR impulse contribution at the finite kernel boundary below
1e-5 in `../native-glare-six-sigma.log`. This is numerical evidence, not visual
acceptance of arbitrary lighting or a calibrated optical point spread function.

Actual Lab/Iris completed midday Sun, west-facing afternoon Sun and rotating
underwater scenes, with no fallback. The native audit validates 94 sequence
PNGs. Visual inspection of the midday final screenshot shows a rounder, softer
bright footprint than v6's visibly squared shoulder. The source disk angle and
illumination remain unchanged. Cloud/wave phases are not independently locked
across packets; no exact before/after subtraction is claimed. Full Sun acceptance
still requires the other retained views and a qualified comparison.

Normal configuration and Mods were restored exactly, ordinary save hashes are
unchanged, and the client exited normally. The normal pack was not replaced.
The larger bounded kernel remains a candidate. Capture overhead contaminates
the short timing samples; clean postprocess cost is not established. Dark
underwater offscreen reflections and strongly distorted boundary remain open.
