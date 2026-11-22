package dev.aqualumen.profiler;

/** Only profiler callbacks cross this boundary. The game's own draw/dispatch stays outside it. */
public final class SafeHooks {
    private static volatile int failures;
    static int errors(){return failures;}
    private static synchronized void disable(String hook,Throwable failure){
        failures++;
        System.err.println("AQ_PROFILE_INVALID errors="+failures+" hook="+hook+" "+failure);
        failure.printStackTrace(System.err);
    }
    public static void frameStart(Object client){
        if(failures!=0) return;
        try{Timers.frameStart(client);}
        catch(Throwable error){disable("frameStart",error);}
    }
    public static void frameEnd(){
        if(failures!=0) return;
        try{Timers.frameEnd();}
        catch(Throwable error){disable("frameEnd",error);}
    }
    public static void leaveFrame(){
        if(failures!=0) return;
        try{Timers.leaveFrame();}
        catch(Throwable error){disable("leaveFrame",error);}
    }
    public static void shutdown(){
        if(failures!=0) return;
        try{Timers.shutdown();}
        catch(Throwable error){disable("shutdown",error);}
    }
    public static void open(String name){
        if(failures!=0) return;
        try{Timers.open(name);}
        catch(Throwable error){disable("open",error);}
    }
    public static void close(){
        if(failures!=0) return;
        try{Timers.close();}
        catch(Throwable error){disable("close",error);}
    }
    public static void countDraw(){
        if(failures!=0) return;
        try{Timers.countDraw();}
        catch(Throwable error){disable("countDraw",error);}
    }
    public static void register(Object program,Object source){
        if(failures!=0) return;
        try{Timers.register(program,source);}
        catch(Throwable error){disable("register",error);}
    }
    public static void pass(Object pass){
        if(failures!=0) return;
        try{Timers.pass(pass);}
        catch(Throwable error){disable("pass",error);}
    }
    public static void endPass(){
        if(failures!=0) return;
        try{Timers.endPass();}
        catch(Throwable error){disable("endPass",error);}
    }
    public static void select(Object program){
        if(failures!=0) return;
        try{Timers.select(program);}
        catch(Throwable error){disable("select",error);}
    }
    public static void draw(boolean compute){
        if(failures!=0) return;
        try{Timers.draw(compute);}
        catch(Throwable error){disable("draw",error);}
    }
    public static void terrain(Object pass){
        if(failures!=0) return;
        try{Timers.terrain(pass);}
        catch(Throwable error){disable("terrain",error);}
    }
    public static void entityFlush(){
        if(failures!=0) return;
        try{Timers.entityFlush();}
        catch(Throwable error){disable("entityFlush",error);}
    }
    public static void reload(){
        if(failures!=0) return;
        try{Timers.reload();}
        catch(Throwable error){disable("reload",error);}
    }
}
