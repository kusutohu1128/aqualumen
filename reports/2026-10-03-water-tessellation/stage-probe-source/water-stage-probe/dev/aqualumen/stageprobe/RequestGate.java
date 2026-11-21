package dev.aqualumen.stageprobe;

/** Pure TEST-only request admission; caller must have validated scope before claim. */
public final class RequestGate {
    private final java.util.Set<String> consumed=new java.util.HashSet<>();
    private long lastAttempt;
    public synchronized boolean claim(String requestId,long nowNanos) {
        try {
            if(requestId==null||!java.util.UUID.fromString(requestId).toString().equals(requestId))return false;
        } catch(IllegalArgumentException rejected){return false;}
        if(consumed.size()>=8||consumed.contains(requestId))return false;
        if(!consumed.isEmpty()&&nowNanos-lastAttempt<1_000_000_000L)return false;
        consumed.add(requestId);lastAttempt=nowNanos;return true;
    }
}
