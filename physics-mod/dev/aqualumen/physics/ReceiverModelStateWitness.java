package dev.aqualumen.physics;

import java.util.List;
import java.util.Objects;
import java.util.function.Function;

public final class ReceiverModelStateWitness {
    public record Owner(int x, int y, int z, String state) {
        public Owner {
            if (state == null || state.isEmpty()) throw new IllegalArgumentException("Unavailable model owner state");
        }
    }
    private ReceiverModelStateWitness() {}
    private record Position(int x,int y,int z) {}
    public static void verifyComplete(List<Owner> expected,List<Owner> captured,Function<Owner,String> read,Runnable guard) {
        Objects.requireNonNull(guard);guard.run();
        var expectedMap=new java.util.HashMap<Position,Owner>();
        var capturedMap=new java.util.HashMap<Position,Owner>();
        for(var owner:List.copyOf(expected))
            if(expectedMap.put(new Position(owner.x(),owner.y(),owner.z()),owner)!=null)
                throw new IllegalArgumentException("Duplicate expected model owner");
        for(var owner:List.copyOf(captured))
            if(capturedMap.put(new Position(owner.x(),owner.y(),owner.z()),owner)!=null)
                throw new IllegalArgumentException("Duplicate captured model owner");
        if(!expectedMap.equals(capturedMap))throw new IllegalStateException("Incomplete or foreign captured model owners");
        verify(expectedMap.values().stream().toList(),read,guard);
    }
    public static void verify(List<Owner> owners, Function<Owner,String> read, Runnable guard) {
        var retained = List.copyOf(owners);
        Objects.requireNonNull(read);Objects.requireNonNull(guard);
        guard.run();
        for (var owner : retained) {
            guard.run();
            if (!owner.state().equals(read.apply(owner)))
                throw new IllegalStateException("Model owner state changed before publication");
        }
        guard.run();
    }
}
