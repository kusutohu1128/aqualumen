package dev.aqualumen.physics;

import org.lwjgl.opengl.*;

public final class ReceiverPlantDrawBinding implements AutoCloseable {
    private static final String[] integerNames={"aqualumenPlantReady","aqualumenPlantMemberships","aqualumenPlantTriangles",
            "aqualumenPlantAtlasOwned","aqualumenPlantMaximumLod"};
    private final Thread owner=Thread.currentThread();
    private final Runnable guard;
    private final int program;
    private final int[] locations=new int[5],previous=new int[5],size=new int[3],offset=new int[3];
    private final float[] reference=new float[3];
    private final int sizeLocation,offsetLocation,referenceLocation,lodLocation;
    private final float lod;
    private ReceiverPlantTextureBinding textures;
    private boolean closed;
    private ReceiverPlantDrawBinding(int program,Runnable guard,int[] locations,int sizeLocation,int offsetLocation,
            int referenceLocation,int lodLocation) {
        this.program=program;this.guard=guard;this.sizeLocation=sizeLocation;this.offsetLocation=offsetLocation;
        this.referenceLocation=referenceLocation;this.lodLocation=lodLocation;
        System.arraycopy(locations,0,this.locations,0,5);
        for(int index=0;index<5;index++)previous[index]=GL20.glGetUniformi(program,locations[index]);
        GL20.glGetUniformiv(program,sizeLocation,size);GL20.glGetUniformiv(program,offsetLocation,offset);
        GL20.glGetUniformfv(program,referenceLocation,reference);lod=GL20.glGetUniformf(program,lodLocation);
    }
    public static ReceiverPlantDrawBinding open(ReceiverPlantPublisher publisher,ReceiverRunPublisher.Window receiver,
            double cameraX,double cameraY,double cameraZ,int atlas,int sampler,float lod,int maximumLod,
            boolean atlasOwned,Runnable guard) {
        java.util.Objects.requireNonNull(publisher);java.util.Objects.requireNonNull(receiver);
        java.util.Objects.requireNonNull(guard);guard.run();
        var packet=publisher.packet();var cells=publisher.publication();
        if(packet==null || cells==null || !cells.owns(packet))throw new IllegalStateException("Plant draw publication unavailable");
        if(!Double.isFinite(cameraX) || !Double.isFinite(cameraY) || !Double.isFinite(cameraZ)
                || !Float.isFinite(lod) || lod<0 || maximumLod<0 || maximumLod>16 || lod>maximumLod)
            throw new IllegalArgumentException("Unqualified plant draw camera/LOD");
        var window=cells.window();
        long[] difference={(long)receiver.x()-window.x(),(long)receiver.y()-window.y(),(long)receiver.z()-window.z()};
        int[] nextOffset=new int[3],limits={192,128,192};
        for(int index=0;index<3;index++) {
            if(difference[index]<-limits[index] || difference[index]>limits[index])
                throw new IllegalArgumentException("Plant draw windows exceed coordinate domain");
            nextOffset[index]=(int)difference[index];
        }
        float[] nextReference={(float)(packet.x()-cameraX),(float)(packet.y()-cameraY),(float)(packet.z()-cameraZ)};
        for(float value:nextReference)if(!Float.isFinite(value) || Math.abs(value)>512)
            throw new IllegalArgumentException("Plant draw reference exceeds bounded domain");
        int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if(program==0)return null;
        int[] locations=new int[5];
        for(int index=0;index<5;index++) {
            locations[index]=GL20.glGetUniformLocation(program,integerNames[index]);
            if(locations[index]<0)return null;
        }
        int size=GL20.glGetUniformLocation(program,"aqualumenPlantSize");
        int offset=GL20.glGetUniformLocation(program,"aqualumenPlantReceiverOffset");
        int reference=GL20.glGetUniformLocation(program,"aqualumenPlantReference");
        int footprint=GL20.glGetUniformLocation(program,"aqualumenPlantLod");
        if(size<0 || offset<0 || reference<0 || footprint<0)return null;
        var binding=new ReceiverPlantDrawBinding(program,guard,locations,size,offset,reference,footprint);
        try {
            GL20.glUniform1i(locations[0],0);
            GL20.glUniform1i(locations[1],cells.memberships());GL20.glUniform1i(locations[2],packet.count());
            GL20.glUniform1i(locations[3],atlasOwned?1:0);GL20.glUniform1i(locations[4],maximumLod);
            GL20.glUniform3i(size,window.width(),window.height(),window.depth());GL20.glUniform3iv(offset,nextOffset);
            GL20.glUniform3fv(reference,nextReference);GL20.glUniform1f(footprint,lod);
            binding.textures=ReceiverPlantTextureBinding.open(publisher,atlas,sampler,guard);
            if(binding.textures==null)throw new IllegalStateException("Plant texture draw contract unavailable");
            guard.run();if(!publisher.ready() || GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=program)
                throw new IllegalStateException("Plant draw owner/program expired");
            GL20.glUniform1i(locations[0],1);
        } catch(RuntimeException error) { binding.close();throw error; }
        return binding;
    }
    public void close() {
        if(Thread.currentThread()!=owner)throw new IllegalStateException("Plant draw state close outside owner");
        if(closed)return;
        guard.run();
        int current=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        try {
            if(!GL20.glIsProgram(program)) {
                if(textures!=null)textures.close();
                throw new IllegalStateException("Plant draw state program was deleted");
            }
            GL20.glUseProgram(program);GL20.glUniform1i(locations[0],0);
            if(textures!=null)textures.close();
            GL20.glUniform3iv(sizeLocation,size);GL20.glUniform3iv(offsetLocation,offset);
            GL20.glUniform3fv(referenceLocation,reference);GL20.glUniform1f(lodLocation,lod);
            for(int index=1;index<5;index++)GL20.glUniform1i(locations[index],previous[index]);
            GL20.glUniform1i(locations[0],previous[0]);closed=true;
        } finally { GL20.glUseProgram(current); }
    }
}
