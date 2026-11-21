package dev.aqualumen.physics;

public final class ReceiverMemberCacheTest {
    public static class Parent {
        private int inherited=7;
        private String hidden="parent";
    }
    public static final class Child extends Parent {
        private String hidden="child";
    }
    public static final class Fixture {
        private Fixture(int value) { }
        public int value(int value) { return value; }
        public int nullable(String value) { return value==null?0:1; }
        public int ambiguous(String value) { return 1; }
        public int ambiguous(Object value) { return 2; }
        public static int shared(byte value) { return value; }
    }
    private static void check(boolean condition) {
        if(!condition) throw new AssertionError("Receiver API metadata cache mismatch");
    }
    private static void missing(ReceiverMemberCache cache,String name,boolean isStatic,Object... arguments) throws Exception {
        try { cache.method(Fixture.class,name,isStatic,arguments); throw new AssertionError("Unavailable API admitted"); }
        catch(NoSuchMethodException expected) { }
    }
    public static void main(String[] arguments) throws Exception {
        var cache=new ReceiverMemberCache();
        var child=new Child();
        var inherited=cache.field(Child.class,"inherited");
        check(inherited==cache.field(Child.class,"inherited") && inherited.getInt(child)==7);
        inherited.setInt(child,19);check(cache.field(Child.class,"inherited").getInt(child)==19);
        check(cache.field(Child.class,"hidden").get(child).equals("child"));
        check(cache.field(Parent.class,"hidden").get(child).equals("parent"));
        var second=new Child();check(inherited.getInt(second)==7);
        try { cache.field(Child.class,"missing");throw new AssertionError("Missing field admitted"); }
        catch(NoSuchFieldException expected) { }
        var constructor=cache.constructor(Fixture.class,1);
        check(constructor==cache.constructor(Fixture.class,2));
        var fixture=constructor.newInstance(3);
        var first=cache.method(Fixture.class,"value",false,1);
        check(first==cache.method(Fixture.class,"value",false,99));
        check(first.invoke(fixture,4).equals(4));
        var nullable=cache.method(Fixture.class,"nullable",false,(Object)null);
        check(nullable.invoke(fixture,(Object)null).equals(0));
        check(cache.method(Fixture.class,"shared",true,(byte)7).invoke(null,(byte)7).equals(7));
        missing(cache,"value",false,(Object)null);
        missing(cache,"value",false,1L);
        missing(cache,"shared",false,(byte)7);
        missing(cache,"ambiguous",false,"value");
        missing(cache,"ambiguous",false,(Object)null);
        var bounded=new ReceiverMemberCache(1);
        bounded.method(Fixture.class,"value",false,1);
        check(bounded.method(Fixture.class,"value",false,2)!=null);
        try { bounded.constructor(Fixture.class,1); throw new AssertionError("Unbounded metadata cache"); }
        catch(IllegalStateException expected) { }
        try { bounded.field(Child.class,"inherited");throw new AssertionError("Fields exceeded shared metadata bound"); }
        catch(IllegalStateException expected) { }
        var fieldBounded=new ReceiverMemberCache(1);
        check(fieldBounded.field(Child.class,"inherited")==fieldBounded.field(Child.class,"inherited"));
        try { fieldBounded.method(Fixture.class,"value",false,1);throw new AssertionError("Methods exceeded shared field bound"); }
        catch(IllegalStateException expected) { }
        System.out.println("PASS receiver API metadata reuse, inherited/hidden fields with fresh per-object values, primitive/null/static/ambiguity/shared-extent controls; not Minecraft timing");
    }
}
