package dev.aqualumen.profiler;

import java.io.InputStream;
import java.util.*;
import java.util.function.Predicate;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.*;
import org.spongepowered.asm.mixin.extensibility.*;
import static org.objectweb.asm.Opcodes.*;

/** The same required-site verifier runs offline and on the actual Mixin target. */
public final class Hooks implements IMixinConfigPlugin {
    static final String IRIS = "net/irisshaders/iris/";
    static final String PIPE = IRIS+"pipeline/", SHADOW = IRIS+"shadows/";
    static final String SODIUM = "net/caffeinemc/mods/sodium/client/render/chunk/";
    static final String ENT = "net/irisshaders/batchedentityrendering/impl/";
    static final String[] TARGETS = {"net/minecraft/class_310", PIPE+"CompositeRenderer",
        SHADOW+"ShadowCompositeRenderer", PIPE+"FinalPassRenderer", PIPE+"IrisRenderingPipeline",
        SHADOW+"ShadowRenderer", SODIUM+"DefaultChunkRenderer", ENT+"FullyBufferedMultiBufferSource"};
    private static final String OBJ = "(Ljava/lang/Object;)V";
    private final Set<String> installed = new HashSet<>();
    private int sites;

    private static MethodNode method(ClassNode c, String name) {
        List<MethodNode> found=c.methods.stream().filter(m -> m.name.equals(name)).toList();
        if(found.size()!=1) throw new IllegalStateException(c.name+"."+name+" count "+found.size());
        return found.getFirst();
    }
    private List<AbstractInsnNode> find(MethodNode m, Predicate<AbstractInsnNode> test, int count) {
        var found=Arrays.stream(m.instructions.toArray()).filter(test).toList();
        if(found.size()!=count) throw new IllegalStateException(m.name+m.desc+" expected "+count+" sites, got "+found.size());
        sites+=count;
        return found;
    }
    private static MethodInsnNode hook(String n,String desc) {
        return new MethodInsnNode(INVOKESTATIC,"dev/aqualumen/profiler/SafeHooks",n,desc,false);
    }
    private static InsnList ops(AbstractInsnNode... instructions) {
        var list=new InsnList();
        for(var i:instructions) list.add(i);
        return list;
    }
    private static InsnList start(String label) {
        return ops(new LdcInsnNode(label), hook("open","(Ljava/lang/String;)V"));
    }
    private static AbstractInsnNode close() {return hook("close","()V");}
    private static Predicate<AbstractInsnNode> call(String owner,String name,String desc) {
        return i -> i instanceof MethodInsnNode v && v.owner.equals(owner) && v.name.equals(name) && v.desc.equals(desc);
    }
    private void around(MethodNode m, Predicate<AbstractInsnNode> target,int n,String label) {
        for(var i:find(m,target,n)){
            m.instructions.insertBefore(i,start(label));
            m.instructions.insert(i,close());
        }
    }
    private void register(ClassNode c,String name) {
        var m=method(c,name);
        var ret=find(m,i->i.getOpcode()==ARETURN,1).getFirst();
        m.instructions.insertBefore(ret,ops(new InsnNode(DUP),new VarInsnNode(ALOAD,1),
                hook("register","(Ljava/lang/Object;Ljava/lang/Object;)V")));
    }
    private void programs(MethodNode m, int count) {
        for(boolean compute:new boolean[]{true,false}){
            int expected=compute?count:1;
            String owner=IRIS+"gl/program/"+(compute?"ComputeProgram":"Program");
            for(var use:find(m,call(owner,"use","()V"),expected))
                m.instructions.insertBefore(use,ops(new InsnNode(DUP),hook("select",OBJ)));
            var op=compute?call(owner,"dispatch","(FF)V"):call(IRIS+"pathways/FullScreenQuadRenderer","renderQuad","()V");
            for(var i:find(m,op,expected)){
                m.instructions.insertBefore(i,ops(new InsnNode(compute?ICONST_1:ICONST_0),hook("draw","(Z)V")));
                m.instructions.insert(i,close());
            }
        }
        around(m,call(IRIS+"gl/IrisRenderSystem","memoryBarrier","(I)V"),1,"barrier");
    }
    private void patch(ClassNode c) {
        if(!installed.add(c.name)) throw new IllegalStateException("duplicate profiler injection "+c.name);
        sites=0;
        String name=c.name.substring(c.name.lastIndexOf('/')+1);
        switch(name){
            case "class_310" -> {
                var m=method(c,"method_1523");
                m.instructions.insertBefore(find(m,i->i.getOpcode()==RETURN,1).getFirst(),hook("leaveFrame","()V"));
                method(c,"close").instructions.insert(hook("shutdown","()V"));
                if(!m.desc.equals("(Z)V")) throw new IllegalStateException(m.desc);
                m.instructions.insert(ops(new VarInsnNode(ALOAD,0),hook("frameStart",OBJ)));
                m.instructions.insertBefore(find(m,call("net/minecraft/class_1041","method_15998","()V"),1).getFirst(),
                        hook("frameEnd","()V"));
            }
            case "CompositeRenderer","ShadowCompositeRenderer","FinalPassRenderer" -> {
                register(c,"createProgram");
                register(c,"createComputes");
                boolean last=name.equals("FinalPassRenderer");
                var m=method(c,last?"renderFinalPass":"renderAll");
                if(!last){
                    var cast=find(m,i->i instanceof TypeInsnNode t && t.getOpcode()==CHECKCAST && t.desc.equals(c.name+"$Pass"),1).getFirst();
                    // The nearest preceding conditional is the outer indexed/iterator loop test.
                    var test=cast.getPrevious();
                    while(test!=null && !(test instanceof JumpInsnNode)) test=test.getPrevious();
                    if(test==null || test.getOpcode()!=(name.equals("CompositeRenderer")?IF_ICMPGE:IFEQ))
                        throw new IllegalStateException("unexpected pass loop "+name);
                    m.instructions.insertBefore(test,hook("endPass","()V"));
                    m.instructions.insert(cast,ops(new InsnNode(DUP),hook("pass",OBJ)));
                }
                programs(m,1);
            }
            case "IrisRenderingPipeline" -> {
                register(c,"createShadowComputes");
                register(c,"createSetupComputes");
                String[] methods={"beginLevelRendering","renderShadows","beginTranslucents","finalizeLevelRendering"};
                String[] stages={"begin","prepare","deferred","composite"};
                for(int i=0;i<methods.length;i++) around(method(c,methods[i]),call(PIPE+"CompositeRenderer","renderAll","()V"),1,"stage/"+stages[i]);
                around(method(c,"finalizeLevelRendering"),call(PIPE+"FinalPassRenderer","renderFinalPass","()V"),1,"stage/final");
                for(String n:List.of("<init>","beginLevelRendering")){
                    var m=method(c,n);
                    int count=n.equals("<init>")?1:2;
                    for(var i:find(m,call(IRIS+"gl/program/ComputeProgram","use","()V"),count))
                        m.instructions.insertBefore(i,ops(new InsnNode(DUP),hook("select",OBJ)));
                    for(var i:find(m,call(IRIS+"gl/program/ComputeProgram","dispatch","(FF)V"),count)){
                        m.instructions.insertBefore(i,ops(new InsnNode(ICONST_1),hook("draw","(Z)V")));
                        m.instructions.insert(i,close());
                    }
                }
                method(c,"destroy").instructions.insert(hook("reload","()V"));
            }
            case "ShadowRenderer" -> {
                var m=method(c,"renderShadows");
                var comp=find(m,call(SHADOW+"ShadowCompositeRenderer","renderAll","()V"),1).getFirst();
                // After the shadow-distance early exit; close capture immediately before shadowcomp.
                var first=find(m,i->i instanceof LdcInsnNode l && "shadows".equals(l.cst),1).getFirst();
                m.instructions.insertBefore(first,start("shadow/capture"));
                m.instructions.insertBefore(comp,close());
                m.instructions.insertBefore(comp,start("stage/shadowcomp"));
                m.instructions.insert(comp,close());
                around(m,call(IRIS+"mixin/LevelRendererAccessor","invokeRenderSectionLayer",
                    "(Lnet/minecraft/class_1921;DDDLorg/joml/Matrix4f;Lorg/joml/Matrix4f;)V"),4,"shadow/terrain");
                around(m,call("net/minecraft/class_4597$class_4598","method_22993","()V"),1,"shadow/entity-flush");
            }
            case "DefaultChunkRenderer" -> {
                var m=method(c,"render");
                if(!m.desc.contains("/terrain/TerrainRenderPass;")) throw new IllegalStateException(m.desc);
                m.instructions.insert(ops(new VarInsnNode(ALOAD,4),hook("terrain",OBJ)));
                m.instructions.insertBefore(find(m,i->i.getOpcode()==RETURN,1).getFirst(),close());
                var batch=find(m,i->i instanceof MethodInsnNode v && v.owner.equals(c.name) && v.name.equals("executeDrawBatch"),1).getFirst();
                m.instructions.insertBefore(batch,hook("countDraw","()V"));
            }
            case "FullyBufferedMultiBufferSource" -> {
                for(String name2:List.of("method_22993","endBatchWithType")){
                    var m=method(c,name2);
                    m.instructions.insert(hook("entityFlush","()V"));
                    m.instructions.insertBefore(find(m,i->i.getOpcode()==RETURN,1).getFirst(),close());
                    var draw=find(m,call(ENT+"BufferSegmentRenderer","drawInner","(L"+ENT+"BufferSegment;)V"),1).getFirst();
                    m.instructions.insertBefore(draw,hook("countDraw","()V"));
                }
            }
            default -> throw new IllegalStateException(c.name);
        }
        System.out.println("AQ_PROFILE_HOOK "+c.name+" sites="+sites);
    }
    public static void main(String[] args) throws Exception {
        Hooks verifier=new Hooks();
        for(String target:TARGETS){
            try(InputStream in=Hooks.class.getClassLoader().getResourceAsStream(target+".class")){
                ClassNode c=new ClassNode();
                new ClassReader(Objects.requireNonNull(in,target)).accept(c,0);
                verifier.patch(c);
            }
        }
    }
    public void postApply(String name,ClassNode c,String mixin,IMixinInfo info){patch(c);}
    public void preApply(String n,ClassNode c,String m,IMixinInfo i){}
    public void onLoad(String p){}
    public String getRefMapperConfig(){return null;}
    public boolean shouldApplyMixin(String n,String m){return true;}
    public void acceptTargets(Set<String>a,Set<String>b){}
    public List<String> getMixins(){return null;}
}
