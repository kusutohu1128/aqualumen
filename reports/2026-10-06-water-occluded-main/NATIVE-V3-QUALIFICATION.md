# v3 result classification correction

v3 compiled its unique binary synchronously and ran actual revised pixel65,53.
The actual GL records and raw data are retained, but the harness returned1:
`INCONCLUSIVE: closed first-floor and non-green negatives`.

Raw readback establishes hidden tag deltaRGB=(0,0,0), while the near first-floor
pixel65,41 changes green by0.09272925555706024 when the farther floor is tagged.
Independent actual-MAIN refracted geometry confirms that pixel's first receiver
is the unchanged near floor, not the tagged far floor. Its source-rejection
behavior is a **renderer requirement under test**, not a fixture qualification
precondition. Therefore its failure must be retained as a distinct RED alongside
the missing hidden-material response, not hidden behind an INCONCLUSIVE label.

v4 changes that classification and saves both results. It does not change the
fixture geometry, shader, material tags, light fields or acceptance thresholds.
The v3 result is not a GREEN or proof of corrected appearance.
