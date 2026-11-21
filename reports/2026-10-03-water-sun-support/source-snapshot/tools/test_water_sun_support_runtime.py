"""Public support telemetry CPU tests; never actual-Iris proof."""
import unittest
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import subprocess
import sys
import tempfile

from water_sun_support_runtime import decode_counts,analyze_reason_point

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=Path(__file__).with_name('water_sun_support_runtime.py')


def support_fixture(directory,mode='reject',observe='reasons'):
    """Synthetic file seam, never an actual current Iris capture."""
    from test_water_snell_main_reason_runtime import reason_fixture
    from water_sun_support_pack import build_pack
    if observe=='inputs':
        from test_water_snell_main_runtime import saved_fixture
        raw_file,_,guard_file=saved_fixture(directory,'stable')
    else:
        raw_file,_,guard_file=reason_fixture(directory,'stable')
    pack=build_pack(ROOT,directory/'synthetic-support.zip',mode,observe)
    raw=json.loads(raw_file.read_text());guard=json.loads(guard_file.read_text())
    identity=dict(packName=pack.name,packSha256=hashlib.sha256(pack.read_bytes()).hexdigest())
    raw.update(identity);guard.update(identity)
    raw_file.write_text(json.dumps(raw));guard_file.write_text(json.dumps(guard))
    return raw_file,pack,guard_file


class SupportCounts(unittest.TestCase):
    def test_same_draw_all48_absent_count_decodes_without_rejection_or_renormalizing(self):
        encoded=48+262144*48
        self.assertEqual(decode_counts(float(encoded)),dict(zero=48,support=0,unknown=0,calls=48))

    def test_complete_certified_zero_application_is_not_a_TIR_or_continuum_zero_claim(self):
        point=dict(reasonTuple=[0,0,0,0],sun_status=[1,1,48+262144*48,0],
            covariance_flags=[.01,0,.01,15],stage=[.2,.3,.5,1])
        result=analyze_reason_point(point,'zero')
        self.assertEqual(result['certificateCounts']['zero'],48)
        self.assertEqual(result['reasonClassification'],'APPLIED')
        self.assertFalse(result['continuousCapZeroProven'])
        self.assertFalse(result['FresnelOrTIRZeroProven'])
        self.assertEqual(point['sun_status'][2],48+262144*48)

    def test_unknown_or_incomplete_loop_never_claims_new_application(self):
        for encoded in (47+262144*47,47+4096+262144*48):
            point=dict(reasonTuple=[0,0,0,0],sun_status=[1,1,encoded,0],
                covariance_flags=[.01,0,.01,15],stage=[.2,.3,.5,1])
            with self.assertRaises(ValueError): analyze_reason_point(point,'zero')

    def test_reject_control_never_claims_certificate_collection(self):
        point=dict(reasonTuple=[3,48,0,0],sun_status=[1,0,0,48],
            covariance_flags=[.01,0,.01,15],stage=[.2,.3,.5,1])
        result=analyze_reason_point(point,'reject')
        self.assertFalse(result['certificateCountsCollected'])
        self.assertEqual(result['reasonClassification'],'CLASSIFIED_LOOP_REJECTION')
        point['sun_status'][2]=64*48+262144*48
        with self.assertRaises(ValueError): analyze_reason_point(point,'reject')

    def test_malformed_packed_counts_cannot_pass_reason_accounting(self):
        for value in (float('nan'),float('inf'),-1,.5,2**24,49,262144,True):
            with self.assertRaises(ValueError): decode_counts(value)

    def test_rejected_unknown_keeps_same_draw_counts_and_old_failure_semantics(self):
        point=dict(reasonTuple=[2,0,0,1],sun_status=[1,0,47+4096+262144*48,1],
            covariance_flags=[.01,0,.01,15],stage=[.2,.3,.5,1])
        result=analyze_reason_point(point,'zero')
        self.assertEqual(result['certificateCounts'],dict(zero=47,support=0,unknown=1,calls=48))
        self.assertEqual(result['reasonClassification'],'CLASSIFIED_LOOP_REJECTION')
        self.assertFalse(result['physicalAccepted'])

    def test_public_saved_cli_qualifies_negative_reject_without_certificate_claim(self):
        with tempfile.TemporaryDirectory(prefix='support-runtime-synthetic-') as temporary:
            directory=Path(temporary);paths=support_fixture(directory)
            before={p.name:p.read_bytes() for p in directory.iterdir()}
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),*map(str,paths)],
                text=True,capture_output=True)
            self.assertEqual(result.returncode,1,result.stderr)
            report=json.loads(result.stdout)
            self.assertEqual(report['mode'],'reject')
            self.assertEqual(report['selectedPoints'],16)
            self.assertEqual(report['qualifiedAppliedPoints'],2)
            self.assertEqual(report['minimumQualifiedAppliedPoints'],4)
            self.assertFalse(report['certificateCountsCollected'])
            self.assertFalse(report['operatorActiveQualified'])
            self.assertFalse(report['physicalAccepted'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in directory.iterdir()})

    def test_public_input_cli_preserves_target_layout_without_TES_or_count_claims(self):
        with tempfile.TemporaryDirectory(prefix='support-input-synthetic-') as temporary:
            directory=Path(temporary);paths=support_fixture(directory,observe='inputs')
            result=subprocess.run([sys.executable,'-B',str(SCRIPT),*map(str,paths)],
                text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout)
            self.assertEqual(report['observe'],'inputs')
            self.assertEqual(report['selectedPoints'],16)
            self.assertEqual(report['firstReasonHistogram']['4'],16)
            self.assertEqual(report['firstTargetExactSupportClasses'],{'1':16})
            self.assertFalse(report['TESObserved'])
            self.assertFalse(report['certificateCountsCollected'])
            self.assertFalse(report['applicationObserved'])
            self.assertFalse(report['physicalAccepted'])

    def test_unknown_certificate_requires_same_draw_other_group_rejection(self):
        counts=64*47+4096+262144*48
        for reason,status in (([0,0,0,0],[1,0,counts,0]),([3,1,0,0],[1,0,counts,1])):
            point=dict(reasonTuple=reason,sun_status=status,covariance_flags=[.01,0,.01,15],
                stage=[.2,.3,.5,1])
            with self.assertRaises(ValueError): analyze_reason_point(point,'zero')

    def test_public_zero_cli_keeps_minimum_four_and_complete_count_boundary(self):
        with tempfile.TemporaryDirectory(prefix='support-zero-synthetic-') as temporary:
            paths=support_fixture(Path(temporary),mode='zero')
            raw=json.loads(paths[0].read_text())
            word=24+64*24+262144*48
            for count in (3,4):
                for index in range(16):
                    raw['samplers'][0]['samples'][index]['rgba']=[0,0,0,0] if index<count else [3,48,0,0]
                    raw['samplers'][1]['samples'][index]['rgba']=[1,1,word,0] if index<count else [1,0,64*48+262144*48,48]
                paths[0].write_text(json.dumps(raw))
                result=subprocess.run([sys.executable,'-B',str(SCRIPT),*map(str,paths)],text=True,capture_output=True)
                self.assertEqual(result.returncode,1 if count==3 else 0,result.stderr)
                report=json.loads(result.stdout)
                self.assertEqual(report['qualifiedAppliedPoints'],count)
                self.assertEqual(report['complete48CertificateLoopPoints'],16)
                self.assertTrue(report['certificateCountsCollected'])
                self.assertFalse(report['all48NodePhysicalClassificationsProven'])
                self.assertFalse(report['continuousCapZeroProven'])
                self.assertFalse(report['physicalAccepted'])

    def test_rehashed_certificate_or_observer_tamper_never_qualifies_source(self):
        from water_sun_support_runtime import pack_policy
        for member in ('shaders/lib/water_sun_support.glsl','shaders/gbuffers_water.fsh'):
            with tempfile.TemporaryDirectory(prefix='support-tamper-synthetic-') as temporary:
                paths=support_fixture(Path(temporary),mode='zero')
                with ZipFile(paths[1]) as archive: files={name:archive.read(name) for name in archive.namelist()}
                files[member]+=b'// synthetic changed source\n'
                metadata=json.loads(files['WATER-SUN-SUPPORT.json'])
                metadata['certificate_sha256' if member.endswith('.glsl') else 'observer_water_fs_sha256']=hashlib.sha256(files[member]).hexdigest()
                files['WATER-SUN-SUPPORT.json']=json.dumps(metadata).encode()
                with ZipFile(paths[1],'w') as archive:
                    for name,content in files.items(): archive.writestr(name,content)
                with self.assertRaises(ValueError): pack_policy(paths[1])

    def test_certified_absent_nodes_cannot_also_count_as_rejected_nodes(self):
        point=dict(reasonTuple=[3,1,0,0],sun_status=[1,0,48+262144*48,1],
            covariance_flags=[.01,0,.01,15],stage=[.2,.3,.5,1])
        with self.assertRaises(ValueError): analyze_reason_point(point,'zero')


if __name__=='__main__': unittest.main(verbosity=2)
