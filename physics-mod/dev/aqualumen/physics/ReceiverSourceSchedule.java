package dev.aqualumen.physics;

public final class ReceiverSourceSchedule {
    private ReceiverRadianceVolume.Epoch attempted;
    public boolean reserve(ReceiverRadianceVolume.Epoch now) {
        if(now==null) return false;
        if(attempted!=null && attempted.world()==now.world() && attempted.resources()==now.resources()
                && now.frame()<=attempted.frame()) return false;
        attempted=now; return true;
    }
    public boolean attempted(ReceiverRadianceVolume.Epoch now) {
        return now!=null && attempted!=null && attempted.world()==now.world()
                && attempted.resources()==now.resources() && now.frame()<=attempted.frame();
    }
    public void reset() { attempted=null; }
}
