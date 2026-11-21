# Minecraft observation intent

The intended claim is that both the pinned ordinary0.6 pack and the bounded land-shadow preview activate in Iris on the RTX3080Ti, produce reviewable images in the three named air-shadow scenes, finish fixture cleanup and restore the prior normal configuration. It is not a speedup, slowdown, 60FPS floor or1440p performance claim.

The pinned benchmark recorder's render-tail intervals exclude scene setup and screenshot operations, discard the first interval and require at least10 intervals. Metadata binds pack hash, real renderer, dimensions, shader state, UUID and camera. We retain those timings as raw telemetry but do not use this image-comparison run to select a performance winner.

Before the run, uptime reported load averages27.30/16.89/14.14 on24logical processors. Other same-user Java processes were busy, while scoped ownership found no running Lab Java. NVIDIA query reported1percentGPU utilization and754MiBused at that instant. Other user processes are outside our authority and will not be stopped. The native fixed-fixture probes measure visibility correctness, not frame timings.

The performance verdict is inconclusive. No independent profiler run, bottleneck attribution, five alternating repetitions or production1440p sweep is part of this unit. A single1600x900image capture sequence per pack cannot establish a performance difference. Error checks, actual pipeline identity and evidence that the requested scene rendered still gate the functional observation.
