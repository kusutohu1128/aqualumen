"""Public synthetic saved-file CPU tests; not Iris/shader evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from test_water_snell_main_runtime import saved_fixture
from water_snell_main_pack import build_pack

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_snell_main_reason_runtime.py')


def reason_fixture(directory,mode,mutate_raw=None,mutate_guard=None,mutate_files=None):
    raw_file,_,guard_file=saved_fixture(directory,mode)
    pack=build_pack(ROOT,directory/'synthetic-main-reasons.zip',mode,observe='reasons')
    if mutate_files:
        with ZipFile(pack) as archive: files={n:archive.read(n) for n in archive.namelist()}
        mutate_files(files)
        with ZipFile(pack,'w') as archive:
            for name,value in files.items(): archive.writestr(name,value)
    raw=json.loads(raw_file.read_text());guard=json.loads(guard_file.read_text())
    for i in range(16):
        raw['samplers'][0]['samples'][i]['rgba']=[0,0,0,0] if i<2 else [3,48,0,0]
        raw['samplers'][1]['samples'][i]['rgba']=[1,1,0,0] if i<2 else [1,0,0,48]
        raw['samplers'][3]['samples'][i]['rgba']=[.1+i/100,.2,.7-i/100,1]
    identity=dict(packName=pack.name,packSha256=hashlib.sha256(pack.read_bytes()).hexdigest())
    raw.update(identity);guard.update(identity)
    if mutate_raw: mutate_raw(raw)
    if mutate_guard: mutate_guard(guard)
    raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
    return raw_file,pack,guard_file


class PublicReasonRuntime(unittest.TestCase):
    def invoke(self,mode='old',**changes):
        with tempfile.TemporaryDirectory(prefix='snell-reasons-synthetic-') as temporary:
            directory=Path(temporary);paths=reason_fixture(directory,mode,**changes)
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),*map(str,paths)],text=True,capture_output=True)
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})
            return result

    def test_public_cli_reports_valid_negative_old_reason_evidence(self):
        result=self.invoke()
        self.assertEqual(result.returncode,1,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['mode'],'old')
        self.assertTrue(report['reasonEvidenceQualified'])
        self.assertEqual(report['selectedPoints'],16)
        self.assertEqual(report['qualifiedAppliedPoints'],2)
        self.assertEqual(report['applicationVerdict'],'NEGATIVE_INSUFFICIENT_APPLICATION')
        self.assertFalse(report['operatorActiveQualified'])
        self.assertFalse(report['physicalAccepted'])
        self.assertFalse(report['sameFrameProven'])

    def test_stable_reason_two_does_not_claim_old_discriminant_or_arithmetic_cause(self):
        def inverse_gate(raw):
            for point in raw['samplers'][0]['samples'][2:]: point['rgba']=[2,0,0,48]
        result=self.invoke(mode='stable',mutate_raw=inverse_gate)
        self.assertEqual(result.returncode,1,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['mode'],'stable')
        self.assertEqual(report['firstReasonHistogram']['2'],14)
        self.assertEqual(report['firstReasonCategories']['2'],'inverse_node_status_rejection')
        self.assertIn('status0 versus status-1 is NOT exported',report['category2Scope'])
        self.assertFalse(report['GPUArithmeticCauseProven'])
        self.assertFalse(report['coefficientClosureObserved'])

    def test_exact_minimum_four_qualifies_only_selected_application(self):
        def applied(count):
            def change(raw):
                for i in range(count):
                    raw['samplers'][0]['samples'][i]['rgba']=[0,0,0,0]
                    raw['samplers'][1]['samples'][i]['rgba']=[1,1,0,0]
            return change
        for count in (3,4):
            result=self.invoke(mode='stable',mutate_raw=applied(count))
            self.assertEqual(result.returncode,1 if count==3 else 0,result.stderr)
            report=json.loads(result.stdout)
            self.assertEqual(report['qualifiedAppliedPoints'],count)
            self.assertEqual(report['minimumQualifiedAppliedPoints'],4)
            self.assertEqual(report['operatorActiveQualified'],count==4)
            for key in ('physicalAccepted','pixelAAAccepted','energyAccepted','shippingAccepted'):
                self.assertFalse(report[key])

    def test_uncategorized_pre_post_fallback_remains_distinct_from_counted_loop(self):
        def unclassified(raw):
            raw['samplers'][0]['samples'][2]['rgba']=[0,0,0,0]
            raw['samplers'][1]['samples'][2]['rgba']=[1,0,0,1]
        result=self.invoke(mutate_raw=unclassified)
        self.assertEqual(result.returncode,1,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['unclassifiedRejectedPoints'],1)
        self.assertEqual(report['points'][2]['reasonClassification'],'UNCLASSIFIED_PRE_OR_POST_LOOP_REJECTION')
        self.assertEqual(report['loopRejectedPoints'],13)

    def test_malformed_accounting_fixed_coordinates_and_guard_are_rejected(self):
        changes=[dict(mutate_raw=lambda r:r['samplers'][0]['samples'][2].update(rgba=[3,47,0,0])),
            dict(mutate_raw=lambda r:r['samplers'][0]['samples'][0].update(x=802)),
            dict(mutate_raw=lambda r:r['samplers'][3]['samples'][0].update(rgba=[.2,.2,.2,1])),
            dict(mutate_raw=lambda r:r['stateAfter'].update(binding=999)),
            dict(mutate_guard=lambda g:g['uniform'].update(value=0)),
            dict(mutate_guard=lambda g:g['uniform'].update(type=5126))]
        for change in changes:
            result=self.invoke(**change)
            self.assertEqual(result.returncode,1)
            self.assertEqual(result.stdout,'')
            self.assertIn('Rejected Snell main reason observation:',result.stderr)

    def test_rehashed_adapted_module_and_observer_changes_cannot_hide_in_recovery_tags(self):
        def node(files):
            member='shaders/lib/water_snell_inverse.glsl'
            files[member]+=b'// altered actual node\n'
            metadata=json.loads(files['WATER-SNELL-MAIN.json'])
            metadata['node_adapted_sha256']=hashlib.sha256(files[member]).hexdigest()
            files['WATER-SNELL-MAIN.json']=json.dumps(metadata).encode()
        def observer(files):
            member='shaders/gbuffers_water.fsh'
            files[member]=files[member].replace(b'gl_FragData[1]=WNS_reasons;',b'gl_FragData[1]=WR_coefficients;')
        for mutation in (node,observer):
            result=self.invoke(mode='stable',mutate_files=mutation)
            self.assertEqual(result.returncode,1)
            self.assertEqual(result.stdout,'')
            self.assertIn('Rejected Snell main reason observation:',result.stderr)


if __name__=='__main__': unittest.main(verbosity=2)
