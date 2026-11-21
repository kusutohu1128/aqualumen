package dev.aqualumen.suntest;

/** Pure bounded admission; caller must first validate actual idle TEST scope. */
public final class SunRequestGate {
    private final java.util.Set<String> used=new java.util.HashSet<>();private long last;
    public synchronized boolean claim(String id,long now) {
        try {if(id==null||!java.util.UUID.fromString(id).toString().equals(id))return false;}
        catch(IllegalArgumentException rejected){return false;}
        if(used.size()>=8||used.contains(id)||(!used.isEmpty()&&now-last<1_000_000_000L))return false;
        used.add(id);last=now;return true;
    }
}
