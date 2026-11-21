package dev.aqualumen.physics;

import org.lwjgl.opengl.*;

public final class ReceiverTextureBinding implements AutoCloseable {
    private final Thread owner=Thread.currentThread();
    private final int program,readyLocation,sizeLocation,originLocation,modeLocation,countLocation;
    private final int ready,mode,count;
    private final int[] size=new int[3],units,textures;
    private final float[] origin=new float[3];
    private boolean closed;
    private ReceiverTextureBinding(int program,int readyLocation,int sizeLocation,int originLocation,int modeLocation,int countLocation,int slots) {
        this.program=program;this.readyLocation=readyLocation;this.sizeLocation=sizeLocation;this.originLocation=originLocation;
        this.modeLocation=modeLocation;this.countLocation=countLocation;units=new int[slots];textures=new int[slots];
        ready=GL20.glGetUniformi(program,readyLocation);
        mode=modeLocation<0?0:GL20.glGetUniformi(program,modeLocation);
        count=countLocation<0?0:GL20.glGetUniformi(program,countLocation);
        GL20.glGetUniformiv(program,sizeLocation,size);GL20.glGetUniformfv(program,originLocation,origin);
    }
    static ReceiverTextureBinding open(int[] nextTextures,int[] nextSize,float[] nextOrigin,int mode,int records) {
        if(nextTextures==null || nextSize==null || nextOrigin==null || nextSize.length!=3 || nextOrigin.length!=3
            || mode!=0 && mode!=1 || nextTextures.length!=(mode==1?6:4)
            || mode==1 && (records<1 || records>65536) || mode==0 && records!=0)
            throw new IllegalArgumentException("Receiver draw layout invalid");
        for(int index=0;index<3;index++)
            if(nextSize[index]<1 || nextSize[index]>(mode==1 && index!=1?96:64) || !Float.isFinite(nextOrigin[index]))
                throw new IllegalArgumentException("Receiver draw bounds invalid");
        for(int texture:nextTextures)if(texture<=0 || !GL11.glIsTexture(texture))throw new IllegalStateException("Receiver draw allocation unavailable");
        int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if(program==0)return null;
        int ready=GL20.glGetUniformLocation(program,"aqualumenReceiverReady");
        int size=GL20.glGetUniformLocation(program,"aqualumenReceiverSize");
        int origin=GL20.glGetUniformLocation(program,"aqualumenReceiverOrigin");
        int runMode=GL20.glGetUniformLocation(program,"aqualumenReceiverRunMode");
        int runCount=GL20.glGetUniformLocation(program,"aqualumenReceiverRunCount");
        if(ready<0 || size<0 || origin<0 || mode==1 && (runMode<0 || runCount<0))return null;
        String[] names={"aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces",
            "aqualumenReceiverRunHeaders","aqualumenReceiverRunRanges"};
        var binding=new ReceiverTextureBinding(program,ready,size,origin,runMode,runCount,nextTextures.length);
        for(int index=0;index<nextTextures.length;index++) {
            int location=GL20.glGetUniformLocation(program,names[index]);
            if(location<0)return null;
            int unit=GL20.glGetUniformi(program,location);
            if(unit<0 || unit>=GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS))return null;
            for(int previous=0;previous<index;previous++)if(binding.units[previous]==unit)
                throw new IllegalStateException("Receiver draw samplers alias one unit");
            binding.units[index]=unit;
        }
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for(int index=0;index<nextTextures.length;index++) {
                int unit=binding.units[index];GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
                binding.textures[index]=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
                int sampler=GL.getCapabilities().OpenGL33 || GL.getCapabilities().GL_ARB_sampler_objects
                    ?GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit):0;
                if(sampler!=0 && GL33.glGetSamplerParameteri(sampler,GL14.GL_TEXTURE_COMPARE_MODE)!=GL11.GL_NONE)
                    throw new IllegalStateException("Receiver draw sampler comparison is incompatible");
            }
            for(int index=0;index<nextTextures.length;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+binding.units[index]);GL11.glBindTexture(GL11.GL_TEXTURE_2D,nextTextures[index]);
            }
            GL20.glUniform3iv(size,nextSize);GL20.glUniform3fv(origin,nextOrigin);
            if(runMode>=0)GL20.glUniform1i(runMode,mode);
            if(runCount>=0)GL20.glUniform1i(runCount,records);
            GL20.glUniform1i(ready,2);return binding;
        } finally { GL13.glActiveTexture(active); }
    }
    @Override public void close() {
        if(Thread.currentThread()!=owner)throw new IllegalStateException("Receiver draw thread owner changed");
        if(closed)return;
        if(GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)!=program)throw new IllegalStateException("Receiver draw program owner changed");
        GL20.glUniform1i(readyLocation,ready);GL20.glUniform3iv(sizeLocation,size);GL20.glUniform3fv(originLocation,origin);
        if(modeLocation>=0)GL20.glUniform1i(modeLocation,mode);
        if(countLocation>=0)GL20.glUniform1i(countLocation,count);
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            for(int index=0;index<textures.length;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]);GL11.glBindTexture(GL11.GL_TEXTURE_2D,textures[index]);
            }
            for(int index=0;index<textures.length;index++) {
                GL13.glActiveTexture(GL13.GL_TEXTURE0+units[index]);
                if(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)!=textures[index])throw new IllegalStateException("Receiver draw texture restoration failed");
            }
        } finally { GL13.glActiveTexture(active); }
        int[] restoredSize=new int[3];float[] restoredOrigin=new float[3];
        GL20.glGetUniformiv(program,sizeLocation,restoredSize);GL20.glGetUniformfv(program,originLocation,restoredOrigin);
        if(GL20.glGetUniformi(program,readyLocation)!=ready
            || modeLocation>=0 && GL20.glGetUniformi(program,modeLocation)!=mode
            || countLocation>=0 && GL20.glGetUniformi(program,countLocation)!=count
            || !java.util.Arrays.equals(size,restoredSize) || !java.util.Arrays.equals(origin,restoredOrigin))
            throw new IllegalStateException("Receiver draw uniform restoration failed");
        closed=true;
    }
}
