package dev.aqualumen.profiler;

public final class QueryPolicyTest {
    public static void main(String[] args) {
        QueryPolicy p=new QueryPolicy();
        assert p.enter();
        assert !p.enter();
        assert !p.outer();
        p.leave();
        assert p.outer();
        p.leave();
        assert p.enter();
        assert !QueryPolicy.harvest(15,8,8);
        assert QueryPolicy.harvest(16,8,8);
        assert !QueryPolicy.harvest(40,0,8);
        assert QueryPolicy.room(252,2,256);
        assert !QueryPolicy.room(253,2,256);
        System.out.println("QueryPolicy nesting, lag and marker reservation OK");
    }
}
