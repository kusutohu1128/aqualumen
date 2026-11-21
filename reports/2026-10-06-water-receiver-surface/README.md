# Retained preparation failure, not material evidence

The first offline surface replay stopped before compilation or execution.
The preparer compared whole requested records when deduplicating face owners.
Two rays hit different positions on the same face, with different point pixels;
the face descriptor itself is identical. Treating point samples as descriptor
identity incorrectly rejected those legitimate duplicate owners. No game, world,
GPU, old packet or producer source was changed. This path is retained untouched.

The corrected preparer compares all descriptor fields except the three explicit
savedPoint fields, while preserving each ray's individual expected texel.
Its new exclusive output is ../2026-10-06-water-receiver-surface-v2/.
