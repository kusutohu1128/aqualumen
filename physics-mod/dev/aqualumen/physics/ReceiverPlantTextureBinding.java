package dev.aqualumen.physics;

import org.lwjgl.opengl.*;

public final class ReceiverPlantTextureBinding implements AutoCloseable {
    private static final String[] names={"aqualumenPlantHeaders","aqualumenPlantIndices","aqualumenPlantPrimitives"};
    private final Thread owner=Thread.currentThread();
    private final Runnable guard;
    private final int[] units,textures,samplers;
    private boolean closed;
    private ReceiverPlantTextureBinding(Runnable guard,int[] units) {
        this.guard=guard;this.units=units;this.textures=new int[units.length];this.samplers=new int[units.length];
    }
    private static boolean numeric(int type) {
        return switch(type) {
            case GL11.GL_FLOAT,GL11.GL_INT,GL20.GL_BOOL,GL20.GL_FLOAT_VEC2,GL20.GL_FLOAT_VEC3,GL20.GL_FLOAT_VEC4,
                    GL20.GL_INT_VEC2,GL20.GL_INT_VEC3,GL20.GL_INT_VEC4,GL20.GL_BOOL_VEC2,GL20.GL_BOOL_VEC3,GL20.GL_BOOL_VEC4,
                    GL20.GL_FLOAT_MAT2,GL20.GL_FLOAT_MAT3,GL20.GL_FLOAT_MAT4,
                    GL21.GL_FLOAT_MAT2x3,GL21.GL_FLOAT_MAT2x4,GL21.GL_FLOAT_MAT3x2,GL21.GL_FLOAT_MAT3x4,
                    GL21.GL_FLOAT_MAT4x2,GL21.GL_FLOAT_MAT4x3,GL11.GL_UNSIGNED_INT,
                    GL30.GL_UNSIGNED_INT_VEC2,GL30.GL_UNSIGNED_INT_VEC3,GL30.GL_UNSIGNED_INT_VEC4 -> true;
            default -> false;
        };
    }
    public static ReceiverPlantTextureBinding open(ReceiverPlantPublisher publisher,Runnable guard) {
        return open(publisher,0,0,false,guard);
    }
    public static ReceiverPlantTextureBinding open(ReceiverPlantPublisher publisher,int atlas,int sampler,Runnable guard) {
        return open(publisher,atlas,sampler,true,guard);
    }
    private static ReceiverPlantTextureBinding open(ReceiverPlantPublisher publisher,int atlas,int sampler,boolean bindAtlas,Runnable guard) {
        java.util.Objects.requireNonNull(publisher);java.util.Objects.requireNonNull(guard);guard.run();
        if(!publisher.ready())throw new IllegalStateException("Plant publication is unavailable");
        var packet=publisher.packet();var material=publisher.material();
        int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if(program==0)return null;
        boolean bindMaterial=GL20.glGetUniformLocation(program,"aqualumenPlantMaterial")>=0;
        if(bindMaterial && publisher.materialTexture()==0)
            throw new IllegalStateException("Plant draw material publication unavailable");
        var selectedNames=new java.util.ArrayList<String>(java.util.Arrays.asList(names));
        if(bindMaterial)selectedNames.add("aqualumenPlantMaterial");
        if(bindAtlas)selectedNames.add("aqualumenPlantAtlas");
        String[] selected=selectedNames.toArray(String[]::new);
        if(bindAtlas && (atlas<=0 || !GL11.glIsTexture(atlas) || sampler<0 || sampler>0 && !GL33.glIsSampler(sampler)))
            throw new IllegalArgumentException("Unavailable plant atlas/sampler");
        int[] units=new int[selected.length],next=new int[selected.length];
        for(int index=0;index<selected.length;index++) {
            int location=GL20.glGetUniformLocation(program,selected[index]);
            if(location<0)return null;
            units[index]=GL20.glGetUniformi(program,location);
            next[index]=selected[index].equals("aqualumenPlantAtlas")?atlas:
                    selected[index].equals("aqualumenPlantMaterial")?publisher.materialTexture():publisher.texture(index);
            if(units[index]<0 || units[index]>=GL11.glGetInteger(GL20.GL_MAX_TEXTURE_IMAGE_UNITS)
                    || next[index]<=0 || !GL11.glIsTexture(next[index]))
                throw new IllegalArgumentException("Invalid plant draw texture/unit");
            for(int prior=0;prior<index;prior++)if(units[prior]==units[index])
                throw new IllegalArgumentException("Plant draw sampler aliases");
        }
        var extentBuffer=org.lwjgl.BufferUtils.createIntBuffer(1);
        var typeBuffer=org.lwjgl.BufferUtils.createIntBuffer(1);
        for(int index=0;index<GL20.glGetProgrami(program,GL20.GL_ACTIVE_UNIFORMS);index++) {
            String name=GL20.glGetActiveUniform(program,index,extentBuffer,typeBuffer);
            if(java.util.Arrays.asList(selected).contains(name)) {
                if(typeBuffer.get(0)!=GL20.GL_SAMPLER_2D || extentBuffer.get(0)!=1)
                    throw new IllegalArgumentException("Plant sampler uniform type differs");
                continue;
            }
            if(numeric(typeBuffer.get(0)))continue;
            int location=GL20.glGetUniformLocation(program,name);
            if(location<0)continue;
            int extent=extentBuffer.get(0);
            for(int element=0;element<extent;element++) {
                int item=extent==1?location:GL20.glGetUniformLocation(program,
                        name.substring(0,name.lastIndexOf('['))+"["+element+"]");
                if(item<0)throw new IllegalArgumentException("Active resource array ownership unavailable");
                int unit=GL20.glGetUniformi(program,item);
                for(int selectedUnit:units)if(unit==selectedUnit)
                    throw new IllegalArgumentException("Plant units overlap another active resource");
            }
        }
        guard.run();if(!publisher.ready() || publisher.packet()!=packet || publisher.material()!=material)
            throw new IllegalStateException("Plant draw owner or publication changed");
        if(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=program)throw new IllegalStateException("Plant draw program changed");
        var binding=new ReceiverPlantTextureBinding(guard,units);
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for(int index=0;index<units.length;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]);
                binding.textures[index]=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
                binding.samplers[index]=GL11.glGetInteger(GL33.GL_SAMPLER_BINDING);
            }
            for(int index=0;index<units.length;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]);
                GL33.glBindSampler(units[index],selected[index].equals("aqualumenPlantAtlas")?sampler:0);
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,next[index]);
            }
            guard.run();if(!publisher.ready() || publisher.packet()!=packet || publisher.material()!=material
                    || GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=program)
                throw new IllegalStateException("Plant draw publication/program expired");
        } catch(RuntimeException error) { binding.close();throw error; }
        finally { GL13.glActiveTexture(active); }
        return binding;
    }
    public void close() {
        if(Thread.currentThread()!=owner)throw new IllegalStateException("Plant draw close outside owner");
        if(closed)return;
        guard.run();
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for(int index=0;index<units.length;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]);
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,textures[index]);GL33.glBindSampler(units[index],samplers[index]);
            }
        } finally { GL13.glActiveTexture(active); }
        closed=true;
    }
}
