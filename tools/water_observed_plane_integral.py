"""Diagnostic known-window response, never a total offscreen/world-light claim.

The observed source term is integrated only over an explicitly declared plane
window. Unobserved terms are not evaluated or declared physically zero. Retained
legacy source units, Gaussian mass, raw optics and .06m facet offset unchanged.
Optional exact-plane edge fade has NO coarse SSR confidence/path approximation.
"""
import math
import water_supported_conditioned as model
import water_supported_probability_rule as probability
import water_supported_rotated as rotated
import water_observed_plane_partition as observed


def smoothstep(lo, hi, value):
    t = min(1.0, max(0.0, (value-lo)/(hi-lo)))
    return t*t*(3-2*t)


def integrate(p, matrix, projection, origin, distance, order, window_partition=True, edge=False, fade_knots=False):
    rule = probability.probability_rule(order)
    q, b = rotated.basis(p)
    terms = []
    evaluated = known = 0
    panel_counts = []
    for ux, wx in rule:
        x = model.NORMAL.inv_cdf(ux)
        if abs(x) >= 8:
            continue
        spans = (observed.partition(p, matrix, projection, origin, distance, x, fade_knots=fade_knots and edge)
                 if window_partition else rotated.intervals(p, q, b, x, 1))
        panel_counts.append(len(spans))
        for lo, hi in spans:
            for uz, wz in rule:
                z, mass = model.conditional_z([(lo, hi)], uz)
                node, plane = observed.plane_node(p, matrix, projection, origin, distance, x, z)
                assert node['supported']
                evaluated += 1
                if plane['kind'] != 'observed-plane':
                    assert not window_partition
                    continue
                known += 1
                fade = 1.0
                if edge:
                    u, v = plane['screen']
                    fade = smoothstep(0.0, .08, min(u, v, 1-u, 1-v))
                source = .125*math.exp(-.085*plane['distance'])*fade
                terms.append(wx*wz*mass*node['transfer']*source)
    return dict(order=order, knownWindowGreen=math.fsum(terms), sourceEvaluations=evaluated,
        knownWindowEvaluations=known, conditionalPanelCounts=panel_counts,
        windowPartition=window_partition, exactPlaneEdgeFade=edge,
        edgeKnotsSplit=fade_knots and edge and window_partition,
        survivorMassFitted=False, outsideWorldLightEvaluated=False,
        coarseSSRReplayed=False, intervalCertified=False)
