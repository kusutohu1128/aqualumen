package dev.aqualumen.physics;

import java.lang.invoke.MethodType;

public final class ReceiverGeometryMethodTest {
    public record Position(int x,int y,int z) { }
    public interface View { Position block(Position position); }
    public static final class Chunk implements View {
        public Position block(Position position) { return position; }
    }
    public static final class State {
        public boolean full(View view,Position position) {
            return view.block(position)==position && position.x()==4 && position.y()==-5 && position.z()==6;
        }
        public float height(View view,Position position) { return full(view,position)?.75f:0; }
        public boolean empty() { return false; }
        public String kind() { return "water"; }
        public String failed() { throw new IllegalStateException("target failure"); }
        public static boolean invalid() { return true; }
    }
    public static void main(String[] arguments) throws Throwable {
        var position=LoadedReceiverWorld.geometryConstructor(Position.class.getConstructor(int.class,int.class,int.class));
        check(position.type().equals(MethodType.methodType(Object.class,int.class,int.class,int.class)),"Primitive constructor signature");
        Object point=(Object)position.invokeExact(4,-5,6);
        check(point.equals(new Position(4,-5,6)),"Exact signed coordinates");
        Object chunk=new Chunk(),state=new State();
        var block=LoadedReceiverWorld.geometryMethod(View.class.getMethod("block",Position.class));
        check((Object)block.invokeExact(chunk,point)==point,"Virtual interface dispatch and object identity");
        var full=LoadedReceiverWorld.geometryMethod(State.class.getMethod("full",View.class,Position.class));
        check((boolean)full.invokeExact(state,chunk,point),"Three-object primitive boolean call");
        var height=LoadedReceiverWorld.geometryMethod(State.class.getMethod("height",View.class,Position.class));
        check((float)height.invokeExact(state,chunk,point)==.75f,"Three-object primitive float call");
        var empty=LoadedReceiverWorld.geometryMethod(State.class.getMethod("empty"));
        check(!(boolean)empty.invokeExact(state),"Owner-only boolean call");
        var kind=LoadedReceiverWorld.geometryMethod(State.class.getMethod("kind"));
        check(((Object)kind.invokeExact(state)).equals("water"),"Erased reference return");
        boolean wrongOwner=false;
        try { Object rejected=(Object)block.invokeExact(state,point); }
        catch(ClassCastException expected) { wrongOwner=true; }
        check(wrongOwner,"Wrong retained owner fails closed");
        boolean failed=false;
        var failure=LoadedReceiverWorld.geometryMethod(State.class.getMethod("failed"));
        try { Object rejected=(Object)failure.invokeExact(state); }
        catch(IllegalStateException expected) { failed=expected.getMessage().equals("target failure"); }
        check(failed,"Target failures are not swallowed");
        boolean staticRejected=false;
        try { LoadedReceiverWorld.geometryMethod(State.class.getMethod("invalid")); }
        catch(IllegalArgumentException expected) { staticRejected=true; }
        check(staticRejected,"Unexpected static API rejected");
        System.out.println("PASS typed geometry methods: exact primitive/reference signatures, retained owner, virtual dispatch, signed coordinates and failure controls; CPU only");
    }
    private static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
}
