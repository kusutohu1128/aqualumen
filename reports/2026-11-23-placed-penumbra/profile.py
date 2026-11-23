"""Measure the shader pass cost on the same witnessed four-torch forest scene."""
import sys
from pack import HERE, WORK, NAME
sys.path.insert(0,str(HERE.parent/"2026-11-23-torch-density"))
import measure_density as density
density.gpu.EXPECTED=density.gpu.EXPECTED|{"dispatch/shadowcomp5","dispatch/shadowcomp6"}
sha="b224ea6f9424ad7dd8424f2c192e1708f97f734a802870cea42ebb722dcb4c02"
sys.argv=[sys.argv[0],"gp-density-placed-hull-gpu","--stages","birch-4","--pack",str(WORK/"ordinary"/NAME),"--sha",sha]
density.main()
