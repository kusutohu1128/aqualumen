# Conditional physical follow-up, not an implemented correction

Root inspected the pinned cap and old residual helper. The cap's new integral
adds `kernel * skyWeight` for transmitted native sunlight only. Its temporary
reflected direction and reflectionTrace alpha do not otherwise enter that sum.
The old full/base residual results have their own independent application gate.
Current source nevertheless rejects the entire new sum for either new reflected
hemisphere or reflected opaque-alpha failure. Reason instrumentation must first
show which predicate actually fails; this inspection alone is not runtime cause.

[Walter et al., Microfacet Models for Refraction through Rough Surfaces,
sections3.2 and4.2](https://www.cs.cornell.edu/~srm/publications/EGSR07-btdf.pdf)
defines sidedness/masking from the actual incident and scattered directions and
derives a distinct transmission half-vector. Root's inference: validation of a
counterfactual reflected ray needs separate justification for a transmission-only
term; it is not automatically a transmission-visibility condition. The source's
missing Smith/multiple scattering and raw-vector conventions limit equivalence
to that complete model. No energy/reciprocity acceptance is inferred.

If actual firstReason3 dominates, the next single implementation seam should
separate transmission validation from counterfactual reflection validation in
the new cap ONLY. Keep old full/base calls/gates, finite inverse bound, actual
transmitted hemisphere and transmitted opaque receiver checks unchanged. Before
modifying that seam, reproduce a valid positive transmitted response with an
invalid counterfactual reflection using public production-main tests, plus actual
opaque-transmission, zero-source, raw-vector reconstruction and guard negatives.
Same fixed16 Iris application/visual evidence and temporal acceptance are still
required after a candidate change. Merely passing source recovery or deleting
all optical guards is not this correction.
