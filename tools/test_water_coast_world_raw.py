"""Real import-chain routing and actual known-water predicate regression."""
import subprocess
import unittest
from water_coast_world_pack import ROOT,OUT
from water_coast_world_raw import require_known_water

class RawRouting(unittest.TestCase):
    def test_previous_import_chain_red_current_chain_green(self):
        old="import water_coast_world_lifecycle as w; import water_coast_stop_raw; assert w.core.OUT==w.OUT"
        fixed="import water_coast_world_raw as w; assert w.core.OUT==w.OUT"
        for label,code,expected in (('previous',old,False),('current',fixed,True)):
            r=subprocess.run(['rtk','proxy','python3','-c',code],cwd=ROOT/'tools',capture_output=True,text=True)
            self.assertEqual(r.returncode==0,expected,label)
    def test_actual_known_mask_and_initialization_clear_rejection(self):
        require_known_water([{'rgba':[1,1,0,1]} for _ in range(16)])
        with self.assertRaises(AssertionError):require_known_water([{'rgba':[0,0,0,0]} for _ in range(16)])

if __name__=='__main__':unittest.main()
