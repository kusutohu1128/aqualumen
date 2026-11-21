package dev.aqualumen.physics;

import java.util.List;

public final class ReceiverModelStateWitnessTest {
    private static void rejected(Runnable action) {
        try { action.run();throw new AssertionError("Changed model owner admitted"); }
        catch (IllegalStateException | IllegalArgumentException expected) {}
    }
    public static void main(String[] arguments) {
        var owner=new ReceiverModelStateWitness.Owner(-17,47,31,"minecraft:grass_block[snowy=false]");
        int[] reads={0},guards={0};
        ReceiverModelStateWitness.verify(List.of(owner),actual->{
            if (!actual.equals(owner)) throw new AssertionError("Owner coordinates changed");
            reads[0]++;return owner.state();
        },()->guards[0]++);
        if(reads[0]!=1 || guards[0]!=3) throw new AssertionError("Fresh state and phase guards required");
        rejected(()->ReceiverModelStateWitness.verify(List.of(owner),actual->"minecraft:grass_block[snowy=true]",()->{}));
        rejected(()->ReceiverModelStateWitness.verify(List.of(owner),actual->null,()->{}));
        var emptyCell=new ReceiverModelStateWitness.Owner(-16,47,31,"minecraft:water[level=0]");
        ReceiverModelStateWitness.verifyComplete(List.of(owner,emptyCell),List.of(emptyCell,owner),actual->actual.state(),()->{});
        rejected(()->ReceiverModelStateWitness.verifyComplete(List.of(owner,emptyCell),List.of(owner),actual->actual.state(),()->{}));
        rejected(()->ReceiverModelStateWitness.verifyComplete(List.of(owner,emptyCell),List.of(owner,owner),actual->actual.state(),()->{}));
        var foreign=new ReceiverModelStateWitness.Owner(-15,47,31,emptyCell.state());
        rejected(()->ReceiverModelStateWitness.verifyComplete(List.of(owner,emptyCell),List.of(owner,foreign),actual->actual.state(),()->{}));
        rejected(()->ReceiverModelStateWitness.verifyComplete(List.of(owner,emptyCell),List.of(owner,emptyCell),actual->
                actual.equals(emptyCell)?"minecraft:kelp[age=0]":actual.state(),()->{}));
        ReceiverModelStateWitness.verify(List.of(owner,emptyCell),actual->actual.state(),()->{});
        rejected(()->ReceiverModelStateWitness.verify(List.of(owner,emptyCell),actual->
                actual.equals(emptyCell)?"minecraft:tall_seagrass[half=lower]":actual.state(),()->{}));
        rejected(()->new ReceiverModelStateWitness.Owner(0,0,0,""));
        rejected(()->ReceiverModelStateWitness.verify(List.of(owner),actual->owner.state(),()->{throw new IllegalStateException("Expired");}));
        int[] phase={0};
        rejected(()->ReceiverModelStateWitness.verify(List.of(owner),actual->owner.state(),()->{
            if(++phase[0]==3) throw new IllegalStateException("Expired after reread");
        }));
        System.out.println("PASS CPU model owner witnesses: exact coordinates/state, same-block property drift, unload and before/after epoch guards; not live mutation acceptance");
    }
}
