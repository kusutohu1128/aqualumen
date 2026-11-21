package dev.aqualumen.physics;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.function.Supplier;

public final class ReceiverCaptureCache<Key,Value> implements AutoCloseable {
    private final Thread owner=Thread.currentThread();
    private final Map<Key,Value> values=new HashMap<>();
    private final int limit;
    private boolean closed;
    private int reads;
    public ReceiverCaptureCache() { this(131072); }
    public ReceiverCaptureCache(int limit) {
        if(limit<1 || limit>1048576) throw new IllegalArgumentException("Invalid capture-cache bound");
        this.limit=limit;
    }
    private void owner() {
        if(closed || Thread.currentThread()!=owner) throw new IllegalStateException("Capture cache has no current owner");
    }
    public Value get(Key key,Supplier<Value> read) {
        owner(); Objects.requireNonNull(key); Objects.requireNonNull(read);
        Value value=values.get(key);
        if(value!=null) return value;
        if(values.size()>=limit) throw new IllegalStateException("Capture cache extent exceeded");
        value=Objects.requireNonNull(read.get()); reads++;
        values.put(key,value); return value;
    }
    public void beginValidation() { owner(); values.clear(); }
    public int reads() { owner(); return reads; }
    public void close() {
        if(Thread.currentThread()!=owner) throw new IllegalStateException("Capture cache close outside owner");
        values.clear(); closed=true;
    }
}
