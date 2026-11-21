package dev.aqualumen.physics;

import java.lang.reflect.Constructor;
import java.lang.reflect.Executable;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class ReceiverMemberCache {
    private record Key(Class<?> owner,String name,boolean isStatic,List<Class<?>> arguments) { }
    private record FieldKey(Class<?> owner,String name) { }
    private final Map<Key,Executable> members=new HashMap<>();
    private final Map<FieldKey,Field> fields=new HashMap<>();
    private final int limit;
    public ReceiverMemberCache() { this(256); }
    public ReceiverMemberCache(int limit) {
        if(limit<1 || limit>256) throw new IllegalArgumentException("Receiver API cache extent invalid");
        this.limit=limit;
    }
    private Key key(Class<?> owner,String name,boolean isStatic,Object[] arguments) {
        var types=new ArrayList<Class<?>>();
        for(Object argument:arguments) types.add(argument==null?Void.class:argument.getClass());
        return new Key(owner,name,isStatic,List.copyOf(types));
    }
    private void put(Key key,Executable member) {
        if(members.size()+fields.size()>=limit) throw new IllegalStateException("Receiver API cache exhausted");
        members.put(key,member);
    }
    public synchronized Method method(Class<?> owner,String name,boolean isStatic,Object... arguments) throws NoSuchMethodException {
        var key=key(owner,name,isStatic,arguments);
        if(members.containsKey(key)) return (Method)members.get(key);
        Method selected=null;
        for(Method candidate:owner.getMethods()) {
            if(!candidate.getName().equals(name) || Modifier.isStatic(candidate.getModifiers())!=isStatic
                    || !matches(candidate.getParameterTypes(),arguments)) continue;
            if(selected!=null) throw new NoSuchMethodException("Ambiguous receiver API: "+name);
            selected=candidate;
        }
        if(selected==null) throw new NoSuchMethodException(owner.getName()+"."+name);
        put(key,selected); return selected;
    }
    public synchronized Constructor<?> constructor(Class<?> owner,Object... arguments) throws NoSuchMethodException {
        var key=key(owner,"<init>",false,arguments);
        if(members.containsKey(key)) return (Constructor<?>)members.get(key);
        for(Constructor<?> constructor:owner.getDeclaredConstructors()) {
            if(!matches(constructor.getParameterTypes(),arguments)) continue;
            constructor.setAccessible(true);
            put(key,constructor); return constructor;
        }
        throw new NoSuchMethodException(owner.getName()+" constructor");
    }
    public synchronized Field field(Class<?> owner,String name) throws NoSuchFieldException {
        var key=new FieldKey(owner,name);
        Field cached=fields.get(key);
        if(cached!=null) return cached;
        for(Class<?> type=owner;type!=null;type=type.getSuperclass()) {
            try {
                Field selected=type.getDeclaredField(name);
                selected.setAccessible(true);
                if(members.size()+fields.size()>=limit) throw new IllegalStateException("Receiver API cache exhausted");
                fields.put(key,selected);return selected;
            } catch(NoSuchFieldException missing) { }
        }
        throw new NoSuchFieldException(name);
    }
    private static boolean matches(Class<?>[] types,Object[] arguments) {
        if(types.length!=arguments.length) return false;
        for(int index=0;index<types.length;index++) {
            if(arguments[index]==null) { if(types[index].isPrimitive()) return false; continue; }
            Class<?> type=types[index];
            if(type==int.class) type=Integer.class;
            if(type==byte.class) type=Byte.class;
            if(!type.isInstance(arguments[index])) return false;
        }
        return true;
    }
}
