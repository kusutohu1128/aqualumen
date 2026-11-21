# Ordinary world lifecycle

Root exclusively owns game/native GL. The previous normal launcher session
14199 was polled live, then terminated normally with exit0 after menu Save and
Quit, followed by title-screen Quit. No force termination or ordinary-world
terrain/time/camera automation was used.

Fresh F2 captures were inspected: paused world at12:18:48 and saved title at
12:20:36. Copies are `ordinary-before-paused.png` and
`ordinary-saved-title.png`. Client log at12:19:16 reports all dimensions saved.
After that save, a new comparison-only private copy of the complete ordinary
world was created under `aqualumen-native-sun.wQBJrT`; it is not a restore plan.
`diff -qr` showed no differences before GL. All java/prismrun PIDs were absent
after ordinary shutdown. Baseline GL owns root session39317.

Before GL, selected `Aqualumen-0.6.0.zip` hash was
`6ceb9cf054efc1cd7240e316bfd81a7225fe9eaf55ad05768f7b26f0744c9a73`,
physics0.2 jar `1e17cf11f642708dbaaf6aea54ae176751d431c819edbf7f0b51647d2c0cce2e`,
options `02516270fea53cc286dceb1d5eca457f2ecc2e0ab6d2e1b15b01c4032307e5f0`,
Iris config `c6606c84241c3a143005947f9d7f0c07094e977dbe0fbe8dab35e9693c6e8b30`,
benchmark properties `45a4c9b0269ec47b3a72fa73647e92702b6012be10f273a60d37f69c9ca148d1`.
The new Sun TEST pack is not installed or selected.

Mechanical failures retained in turn outputs, not renderer RED: one screenshot
copy used a duplicated Prism directory and was corrected; `import` is absent;
Flameshot DISPLAY=:1 capture was black and was not used as UI evidence. A fresh
Minecraft F2 title capture supplied the actual title evidence. One test run
from repository root lacked tools on its import path; rerun from tools passed
all9 tests. One lookup of an inferred old handoff filename was absent; the old
packet was not modified. These are not optical failures or behavioral TDD RED.

## Normal restart after all GL terminated

Root baseline session39317, STUB session31817 and CAP session87540 all ended
exit0. Before restarting, java/prismrun were absent, options/Iris/benchmark
configurations matched their pre-GL copies byte-for-byte, the selected pack and
physics jar retained their hashes, and the entire saved ordinary world matched
the fresh post-save comparison copy. No backup restoration was performed.

Normal MSA startup uses root-owned session30593 and profile kusutohu1128, without
an offline username override. At12:59:06 the actual client set that user;
12:59:07 selected Aqualumen-0.6.0.zip;12:59:12 created the overworld pipeline;
12:59:13 initialized the physics0.2 contact bridge. Live java PID4017144 and
prismrun PID4017051 were observed. Actual Minecraft window62914567 is titled
`Minecraft* 1.21.1 - シングルプレイ` and sized1600x900. The window ID being reused
does not constitute PID/process identity; startup and the new owned session
were checked separately.

Root paused the world and inspected its fresh F2 capture
`screenshots/2026-10-03_13.00.37.png`. Packet copy
`ordinary-restored-paused.png` has SHA256
`8850e540170e59644c987395a948ea246b04953d4363acbd5a267eabd9403a0d`.
It shows the paused normal shore/world, not the new Sun candidate. No ordinary
terrain/time/camera automation or new pack installation was used. The game is
left paused for normal play, and no further native GL is run concurrently.

Options and benchmark configuration remain byte-identical after restart. Iris
settings excluding generated comment lines are unchanged; its new generated
timestamp changes only the file hash to
`b2850a2b30dac77a3c36ff7dce566f552737476bac1cad39d6b39e371f35aca3`.
The existing SoundSystem/OpenAL initialization error recurred at12:59:08; audio
was neither changed nor claimed fixed. Private launcher/account state is not
published. The full ordinary save comparison is made before launch, not after
the world naturally resumes and may update its save.
