import math
import unittest
import water_supported_sampling_cpu as sampling


class SamplingTests(unittest.TestCase):
    def test_base_digits(self):
        self.assertEqual([sampling.radical_inverse(i,2) for i in range(1,5)],[.5,.25,.75,.125])
        self.assertAlmostEqual(sampling.radical_inverse(2,3),2/3)

    def test_gaussian_reproducible_not_fixed_cartesian_lattice(self):
        nodes=list(sampling.slopes(4096,308060))
        self.assertEqual(nodes,list(sampling.slopes(4096,308060)))
        self.assertNotEqual(nodes[:16],list(sampling.slopes(16,308061)))
        for axis in range(2):
            mean=math.fsum(a[axis] for a in nodes)/len(nodes)
            variance=math.fsum(a[axis]**2 for a in nodes)/len(nodes)-mean*mean
            self.assertLess(abs(mean),.01)
            self.assertLess(abs(variance-1),.02)


if __name__=='__main__':unittest.main()
