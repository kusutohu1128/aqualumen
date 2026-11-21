"""Public CPU quadrature contracts, not GLSL or physical acceptance."""
from fractions import Fraction
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import unittest

from water_gh_phase_reference import evaluate


class GHPhaseReference(unittest.TestCase):
    def test_public_nine_positive_fixed_weights_reproduce_covariance(self):
        report = evaluate((4, 1, 3))
        self.assertEqual(report['schema'], 'aqualumen-white-gh-phase-reference-v1')
        self.assertEqual(len(report['nodes']), 9)
        weights = [Fraction(n['weight']) for n in report['nodes']]
        self.assertTrue(all(w > 0 for w in weights))
        self.assertEqual(sum(weights), 1)
        self.assertEqual(report['exact']['mass'], '1')
        self.assertEqual(report['exact']['mean'], ['0', '0'])
        self.assertEqual(report['exact']['covariance'], ['4', '1', '3'])
        self.assertLess(float(report['max_degree4_residual']), 1e-60)

    def test_phase45_preserves_total_degree4_with_correlated_covariance_and_mean(self):
        original = evaluate((4, 1, 3), mean=(Fraction(1, 4), Fraction(-1, 2)))
        rotated = evaluate((4, 1, 3), phase_degrees=45, mean=(Fraction(1, 4), Fraction(-1, 2)))
        self.assertEqual(original['exact'], rotated['exact'])
        self.assertEqual(rotated['exact']['mean'], ['1/4', '-1/2'])
        self.assertEqual({k: rotated['exact']['central_moments'][k] for k in ('40', '31', '22', '13', '04')},
                         {'40': '48', '31': '12', '22': '14', '13': '9', '04': '27'})
        self.assertEqual([n['weight'] for n in original['nodes']], [n['weight'] for n in rotated['nodes']])
        self.assertNotEqual(original['nodes'][0]['perturbation'], rotated['nodes'][0]['perturbation'])
        self.assertTrue(rotated['precision_agreement_80_120'])
        self.assertEqual(rotated['degree_scope'], 'TOTAL degree <=4 only')
        self.assertLess(float(rotated['max_degree4_residual']), 1e-60)

    def test_degenerate_psd_is_retained_and_nonfinite_domain_is_rejected(self):
        for covariance in ((0, 0, 0), (0, 0, 4), (4, 2, 1)):
            for phase in (0, 45):
                report = evaluate(covariance, phase_degrees=phase)
                self.assertEqual(report['exact']['covariance'], list(map(str, covariance)))
                self.assertEqual(len(report['nodes']), 9)
                self.assertTrue(report['precision_agreement_80_120'])
                self.assertLess(float(report['max_degree4_residual']), 1e-60)
        for covariance in ((-1, 0, 1), (1, 2, 1), (0, 1, 1), (1, 0, Decimal('Infinity')),
                           (1, 0, float('nan')), (True, 0, 1)):
            with self.subTest(covariance=covariance), self.assertRaises(ValueError):
                evaluate(covariance)

    def test_anisotropic_rotation_after_cholesky_is_a_wrong_order_counterexample(self):
        report = evaluate((4, 0, 1), phase_degrees=45)
        self.assertEqual(report['exact']['covariance'], ['4', '0', '1'])
        self.assertEqual(report['wrong_order']['covariance'], ['5/2', '3/2', '5/2'])
        self.assertFalse(report['wrong_order']['matches_requested_covariance'])
        self.assertFalse(report['wrong_order']['policyAccepted'])
        self.assertAlmostEqual(float(report['wrong_order']['measured_covariance'][0]), 2.5)
        self.assertAlmostEqual(float(report['wrong_order']['measured_covariance'][1]), 1.5)
        self.assertAlmostEqual(float(report['wrong_order']['measured_covariance'][2]), 2.5)

    def test_sixth_and_degree8_are_not_phase_or_distribution_invariants(self):
        zero = evaluate((1, 0, 1))
        rotated = evaluate((1, 0, 1), phase_degrees=45)
        self.assertEqual(zero['higher_degree']['white_X6'], '9')
        self.assertEqual(rotated['higher_degree']['white_X6'], '27/2')
        self.assertEqual(zero['higher_degree']['gaussian_white_X6'], '15')
        self.assertEqual(zero['higher_degree']['white_X4Z4'], '9')
        self.assertEqual(rotated['higher_degree']['white_X4Z4'], '9/4')
        self.assertEqual(rotated['higher_degree']['gaussian_white_X4Z4'], '9')
        self.assertNotIn('44', rotated['exact']['central_moments'])
        self.assertFalse(rotated['higher_degree']['invarianceAccepted'])
        self.assertFalse(rotated['convergenceAccepted'])
        self.assertAlmostEqual(float(rotated['higher_degree']['measured_white_X6']), 13.5)
        self.assertAlmostEqual(float(rotated['higher_degree']['measured_white_X4Z4']), 2.25)

    def test_binary32_literal_and_unfused_diagnostics_are_separate_and_not_renormalized(self):
        report = evaluate((4, 1, 3), phase_degrees=45)
        diagnostic = report['binary32']
        self.assertTrue(diagnostic['available'])
        self.assertEqual(diagnostic['literals']['nodePositive']['bits'], '3fddb3d7')
        self.assertEqual(diagnostic['literals']['rotation45']['bits'], '3f3504f3')
        self.assertNotEqual(Fraction(diagnostic['product_weight_mass']), 1)
        self.assertEqual(len(diagnostic['nodes']), 9)
        self.assertFalse(diagnostic['weightsRenormalized'])
        self.assertFalse(diagnostic['GPUArithmeticAccepted'])
        self.assertEqual(diagnostic['operation_policy'], 'round-nearest ties-even after each primitive; no FMA')
        self.assertTrue(diagnostic['white_degree4_within_predeclared_bound'])
        self.assertEqual(diagnostic['white_degree4_abs_plus_relative_bound'], '1/131072')
        self.assertEqual(report['exact']['mass'], '1')

    def test_binary32_ties_even_and_rounded_rank1_failure_keep_exact_reference(self):
        lower = evaluate((1 + Fraction(1, 2 ** 24), 0, 1))
        upper = evaluate((1 + Fraction(3, 2 ** 24), 0, 1))
        self.assertEqual(lower['binary32']['rounded_covariance'][0], '1')
        self.assertEqual(upper['binary32']['rounded_covariance'][0], str(1 + Fraction(1, 2 ** 22)))
        rank1 = evaluate((1, Fraction(1, 10), Fraction(1, 100)), phase_degrees=45)
        self.assertTrue(rank1['precision_agreement_80_120'])
        self.assertFalse(rank1['binary32']['available'])
        self.assertLess(Fraction(rank1['binary32']['rounded_schur']), 0)
        self.assertFalse(rank1['binary32']['covarianceRepaired'])
        self.assertFalse(rank1['binary32']['GPUArithmeticAccepted'])

    def test_public_cli_exports_exact_input_math_and_rejects_invalid_phase(self):
        command = [sys.executable, '-B', str(Path(__file__).with_name('water_gh_phase_reference.py')),
                   '--covariance', '4', '1', '3', '--phase', '45', '--mean', '1/4', '-1/2']
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report['exact']['mean'], ['1/4', '-1/2'])
        self.assertEqual(report['exact']['central_moments']['22'], '14')
        self.assertFalse(report['shaderExecuted'])
        process = subprocess.run(command[:command.index('--phase') + 1] + ['46'],
                                 capture_output=True, text=True, check=False)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(process.stdout, '')


if __name__ == '__main__':
    unittest.main(verbosity=2)
