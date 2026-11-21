"""Actual MAIN known in-viewport first-plane visibility regression."""
import os
from pathlib import Path
import unittest
import water_source_boundary_audit as reader


class BoundaryFixTests(unittest.TestCase):
    def test_known_visible_first_plane_is_not_skipped_by_an_offscreen_march_endpoint(self):
        root=Path(os.environ.get('AQ_BOUNDARY_MAIN',
            'reports/2026-10-06-water-source-boundary/fixed-observed-12-01'))
        source=Path(os.environ.get('AQ_BOUNDARY_SOURCES',
            'reports/2026-10-06-water-source-boundary/fixed-observer-12-v1'))
        result=reader.audit(root,source)
        self.assertEqual(result['observedPlaneMisses'],0)
        self.assertEqual(result['hitsOutsideOracleSafetyViewport'],0)


if __name__=='__main__':unittest.main()
