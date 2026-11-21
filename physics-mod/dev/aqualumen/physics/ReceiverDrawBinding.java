package dev.aqualumen.physics;

import net.irisshaders.iris.uniforms.CameraUniforms;
import org.lwjgl.opengl.*;

public final class ReceiverDrawBinding implements AutoCloseable {
    private final ReceiverTextureBinding runBinding;
    private final int program, readyLocation, sizeLocation, originLocation, ready;
    private final int[] size=new int[3], units=new int[4], textures=new int[4];
    private final float[] origin=new float[3];
    private ReceiverDrawBinding(int program,int readyLocation,int sizeLocation,int originLocation) {
        runBinding=null;
        this.program=program; this.readyLocation=readyLocation; this.sizeLocation=sizeLocation; this.originLocation=originLocation;
        ready=GL20.glGetUniformi(program,readyLocation);
        GL20.glGetUniformiv(program,sizeLocation,size); GL20.glGetUniformfv(program,originLocation,origin);
    }
    private ReceiverDrawBinding(ReceiverTextureBinding runBinding) {
        this.runBinding=runBinding;program=readyLocation=sizeLocation=originLocation=ready=0;
    }
    public static ReceiverDrawBinding open(ReceiverRunPublisher publisher,ReceiverRadianceVolume.Epoch now) {
        if(publisher.ready(now)!=2)return null;
        var bounds=publisher.window(now);var camera=CameraUniforms.getUnshiftedCameraPosition();
        int[] textures=new int[6];for(int index=0;index<textures.length;index++)textures[index]=publisher.texture(index,now);
        var binding=ReceiverTextureBinding.open(textures,new int[]{bounds.width(),bounds.height(),bounds.depth()},
            new float[]{(float)(bounds.x()-camera.x),(float)(bounds.y()-camera.y),(float)(bounds.z()-camera.z)},1,publisher.records(now));
        return binding==null?null:new ReceiverDrawBinding(binding);
    }
    public static ReceiverDrawBinding open(ReceiverRadiancePublisher publisher,ReceiverRadianceVolume.Epoch now) {
        if(publisher.ready(now)!=2) return null;
        int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if(program==0) return null;
        int ready=GL20.glGetUniformLocation(program,"aqualumenReceiverReady");
        int size=GL20.glGetUniformLocation(program,"aqualumenReceiverSize");
        int origin=GL20.glGetUniformLocation(program,"aqualumenReceiverOrigin");
        if(ready<0 || size<0 || origin<0) return null;
        String[] names={"aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces"};
        var binding=new ReceiverDrawBinding(program,ready,size,origin);
        for(int index=0;index<4;index++) {
            int location=GL20.glGetUniformLocation(program,names[index]);
            if(location<0) return null;
            int unit=GL20.glGetUniformi(program,location);
            if(unit<0 || unit>=GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS)) return null;
            for(int previous=0;previous<index;previous++) if(binding.units[previous]==unit)
                throw new IllegalStateException("Receiver draw samplers alias one unit");
            binding.units[index]=unit;
        }
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for(int index=0;index<4;index++) {
                int unit=binding.units[index]; GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                binding.textures[index]=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
                int sampler=GL.getCapabilities().OpenGL33 || GL.getCapabilities().GL_ARB_sampler_objects
                        ? GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit) : 0;
                if(sampler!=0 && GL33.glGetSamplerParameteri(sampler,GL14.GL_TEXTURE_COMPARE_MODE)!=GL11.GL_NONE)
                    throw new IllegalStateException("Receiver draw sampler comparison is incompatible");
            }
            var bounds=publisher.bounds(now); var camera=CameraUniforms.getUnshiftedCameraPosition();
            for(int index=0;index<4;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+binding.units[index]);
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,publisher.texture(index,now));
            }
            GL20.glUniform3i(size,bounds.width(),bounds.height(),bounds.depth());
            GL20.glUniform3f(origin,(float)(bounds.x()-camera.x),(float)(bounds.y()-camera.y),(float)(bounds.z()-camera.z));
            GL20.glUniform1i(ready,2);
            return binding;
        } finally { GL13.glActiveTexture(active); }
    }
    @Override public void close() {
        if(runBinding!=null) { runBinding.close();return; }
        if(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=program) throw new IllegalStateException("Receiver draw program owner changed");
        GL20.glUniform1i(readyLocation,ready); GL20.glUniform3iv(sizeLocation,size); GL20.glUniform3fv(originLocation,origin);
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for(int index=0;index<4;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]); GL11.glBindTexture(GL11.GL_TEXTURE_2D,textures[index]);
            }
            for(int index=0;index<4;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]);
                if(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)!=textures[index])
                    throw new IllegalStateException("Receiver draw texture restoration failed");
            }
        } finally { GL13.glActiveTexture(active); }
        if(GL20.glGetUniformi(program,readyLocation)!=ready) throw new IllegalStateException("Receiver draw readiness restoration failed");
        int[] restoredSize=new int[3]; float[] restoredOrigin=new float[3];
        GL20.glGetUniformiv(program,sizeLocation,restoredSize); GL20.glGetUniformfv(program,originLocation,restoredOrigin);
        if(!java.util.Arrays.equals(size,restoredSize) || !java.util.Arrays.equals(origin,restoredOrigin))
            throw new IllegalStateException("Receiver draw bounds restoration failed");
    }
}
