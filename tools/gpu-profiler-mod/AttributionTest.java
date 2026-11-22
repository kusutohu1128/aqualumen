package dev.aqualumen.profiler;

/** Exercises the same lookup that receives Iris's shadow-composite pass object. No GL calls. */
public final class AttributionTest {
    static final class Pass {
        Object program;
        Object[] computes;
        Pass(Object... computes) { this.computes=computes; }
    }
    public static void main(String[] args) {
        Pass empty=new Pass(null,null);
        assert Timers.passLabel(empty,"shadowcomp",8).name().equals("shadowcomp/unnamed-8");
        assert Timers.passLabel(new Pass(),"begin",2).name().equals("begin/unnamed-2");
        assert Timers.passLabel(empty,"shadowcomp",8).empty();
        Pass unknown=new Pass(new Object());
        assert Timers.passLabel(unknown,"prepare",0).name().equals("prepare/unnamed-0");
        assert !Timers.passLabel(unknown,"prepare",0).empty();
        Object mapped=new Object();
        Timers.names.put(mapped,new Timers.ProgramName("pass/shadowcomp4","dispatch/shadowcomp4"));
        assert Timers.passLabel(new Pass(new Object(),mapped),"shadowcomp",4).name().equals("pass/shadowcomp4");
        SafeHooks.leaveFrame();
        assert SafeHooks.errors()==1;
        SafeHooks.leaveFrame();
        assert SafeHooks.errors()==1;
        System.out.println("Empty, unmapped and mapped pass attribution OK");
    }
}
