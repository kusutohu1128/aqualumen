"""Require a newly observed normal pause, not an arbitrary historical pause log."""
def verify_pause_event(log,runtime,pause):
    lines=log.splitlines()
    event=lambda filename:[i for i,line in enumerate(lines) if "スクリーンショットを"+filename+"として保存しました" in line]
    before,after=event(runtime),event(pause)
    if len(before)!=1 or len(after)!=1 or before[0]>=after[0]:
        raise ValueError("Distinct ordered runtime/pause screenshots required")
    pauses=[i for i,line in enumerate(lines) if "Saving and pausing game..." in line and before[0]<i<after[0]]
    if not pauses:raise ValueError("No fresh pause event after the runtime screenshot")
    return dict(runtimeLogLine=before[0]+1,freshPauseLogLine=pauses[-1]+1,pauseScreenshotLogLine=after[0]+1,
                imageMenuMustBeInspectedSeparately=True)
