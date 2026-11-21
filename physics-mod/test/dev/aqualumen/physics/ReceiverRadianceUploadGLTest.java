package dev.aqualumen.physics;

import java.util.Arrays;
import org.lwjgl.glfw.GLFW;
import org.lwjgl.opengl.*;

public final class ReceiverRadianceUploadGLTest {
    public static void main(String[] args) {
        if (!GLFW.glfwInit()) throw new IllegalStateException("GLFW initialization failed");
        GLFW.glfwWindowHint(GLFW.GLFW_VISIBLE, GLFW.GLFW_FALSE);
        long window = GLFW.glfwCreateWindow(16, 16, "Aqualumen upload test", 0, 0);
        if (window == 0) throw new IllegalStateException("GLFW context unavailable");
        try {
            GLFW.glfwMakeContextCurrent(window); GL.createCapabilities();
            String renderer = GL11.glGetString(GL11.GL_RENDERER);
            if (renderer == null || !renderer.contains("NVIDIA")) throw new IllegalStateException("Actual NVIDIA context required");
            System.out.println("Renderer: " + renderer + "; GL: " + GL11.glGetString(GL11.GL_VERSION));
            Thread owner = Thread.currentThread();
            var uploader = new ReceiverRadianceTextureUpload(() -> {
                if (Thread.currentThread() != owner || GLFW.glfwGetCurrentContext() != window)
                    throw new IllegalStateException("Owned test context is not current");
            });
            int guardTexture = GL11.glGenTextures(), guardBuffer = GL15.glGenBuffers();
            GL13.glActiveTexture(GL13.GL_TEXTURE2); GL11.glBindTexture(GL11.GL_TEXTURE_2D, guardTexture);
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER, guardBuffer);
            GL15.glBufferData(GL21.GL_PIXEL_UNPACK_BUFFER, 256, GL15.GL_STREAM_DRAW);
            int[] names = {GL11.GL_UNPACK_ALIGNMENT, GL11.GL_UNPACK_ROW_LENGTH, GL11.GL_UNPACK_SKIP_ROWS,
                           GL11.GL_UNPACK_SKIP_PIXELS, GL11.GL_UNPACK_SWAP_BYTES};
            int[] values = {8,7,2,3,1};
            for (int index = 0; index < names.length; index++) GL11.glPixelStorei(names[index], values[index]);
            float[] pixels = {0,.125f,.25f,1, .5f,.75f,1,0, 2,3,4,1, 8,16,32,1};
            int texture = uploader.create(2, 2, pixels);
            check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE) == GL13.GL_TEXTURE2 &&
                  GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D) == guardTexture &&
                  GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING) == guardBuffer, "Texture/PBO state restoration");
            for (int index = 0; index < names.length; index++) check(GL11.glGetInteger(names[index]) == values[index], "Unpack state restoration");
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, texture);
            float[] actual = new float[pixels.length];
            GL11.glGetTexImage(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, GL11.GL_FLOAT, actual);
            check(Arrays.equals(actual, pixels), "Exact RGBA32F texture readback");
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, guardTexture);
            uploader.delete(texture); check(!GL11.glIsTexture(texture), "Owned texture release");
            for(int width:new int[]{65,4096}) {
                float[] batch=new float[width*4];
                for(int index=0;index<batch.length;index++) batch[index]=index*.125f;
                int wide=uploader.create(width,1,batch);
                check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)==GL13.GL_TEXTURE2
                        && GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==guardTexture
                        && GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING)==guardBuffer,"Wide batch state restoration");
                for(int index=0;index<names.length;index++) check(GL11.glGetInteger(names[index])==values[index],"Wide batch unpack restoration");
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,wide);
                check(GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH)==width,"Wide batch extent");
                float[] readback=new float[batch.length];
                GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,readback);
                check(Arrays.equals(batch,readback),"Wide batch exact float contents");
                GL11.glBindTexture(GL11.GL_TEXTURE_2D,guardTexture);
                uploader.delete(wide); check(!GL11.glIsTexture(wide),"Wide batch release");
            }
            for(int[] extent:new int[][]{{4097,1},{4096,17},{0,1},{1,4097}}) {
                boolean rejected=false;
                try { uploader.create(extent[0],extent[1],new float[Math.max(0,extent[0]*extent[1]*4)]); }
                catch(IllegalArgumentException expected) { rejected=true; }
                check(rejected && GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==guardTexture
                        && GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING)==guardBuffer,"Oversized batch rejection preserves bindings");
            }
            var epoch = new ReceiverRadianceVolume.Epoch(new Object(), 1, 1);
            float[][] paired = {{3,0,0,0}, {.75f,0,0,1}, {.25f,0,0,1}, {0,1,0,1}};
            var volume = new ReceiverRadianceVolume(epoch, new ReceiverField.Bounds(0,0,0,1,1,1), paired[0], paired[1], paired[2], paired[3]);
            var publisher = new ReceiverRadiancePublisher(uploader);
            publisher.publish(volume, epoch);
            check(publisher.ready(epoch) == 2 && GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D) == guardTexture, "Coherent four-texture GPU publication");
            int[] owned = new int[4];
            for (int index = 0; index < 4; index++) {
                owned[index] = publisher.texture(index, epoch);
                GL11.glBindTexture(GL11.GL_TEXTURE_2D, owned[index]);
                float[] readback = new float[4];
                GL11.glGetTexImage(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, GL11.GL_FLOAT, readback);
                check(Arrays.equals(readback, paired[index]), "Published paired GPU contents");
            }
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, guardTexture);
            check(publisher.ready(new ReceiverRadianceVolume.Epoch(epoch.world(), 2, 1)) == 0, "GPU publication expires");
            publisher.close();
            for (int ownedTexture : owned) check(!GL11.glIsTexture(ownedTexture), "Published GPU allocation released");
            runPublication(uploader,epoch,guardTexture,guardBuffer,names,values);
            lightingState(uploader, epoch, owner, window);
            check(GL11.glGetError() == GL11.GL_NO_ERROR, "GL error after upload/readback");
            GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER, 0);
            GL15.glDeleteBuffers(guardBuffer); GL11.glDeleteTextures(guardTexture);
            System.out.println("PASS actual NVIDIA upload/readback, storage, unpack/PBO/binding restoration and release; controlled context guard, not Minecraft integration");
        } finally { GLFW.glfwDestroyWindow(window); GLFW.glfwTerminate(); }
    }

    private static void runPublication(ReceiverRadianceTextureUpload uploader,ReceiverRadianceVolume.Epoch epoch,
                                       int guardTexture,int guardBuffer,int[] names,int[] values) {
        var layout=ReceiverRunLayout.capture(95,36,95,(x,y,z)->new ReceiverRunLayout.Cell(y==10?3:2,0,0,0));
        var radiance=ReceiverRunRadiance.capture(layout,epoch,index->new ReceiverRunRadiance.Sample(epoch,index,
            new float[]{.75f,.5f,.25f,1},new float[]{.1f,.05f,0,1},new float[]{0,1,0,1}));
        var window=new ReceiverRunPublisher.Window(-47,-20,-47,95,36,95);
        int[] calls={0},failure={-1};var created=new java.util.ArrayList<Integer>();
        var publisher=new ReceiverRunPublisher(new ReceiverRadiancePublisher.Upload() {
            public int create(int width,int height,float[] pixels) {
                if(++calls[0]==failure[0])throw new IllegalStateException("Injected sixth run upload failure");
                int texture=uploader.create(width,height,pixels);created.add(texture);return texture;
            }
            public void delete(int texture) { uploader.delete(texture); }
        });
        publisher.publish(window,layout,radiance,epoch);
        float[][] expected={radiance.cells(),radiance.source(),radiance.sun(),radiance.faces(),layout.headers(),
            Arrays.copyOf(layout.ranges(),radiance.width()*radiance.height()*4)};
        int[] previous=new int[6];
        for(int index=0;index<6;index++) {
            previous[index]=publisher.texture(index,epoch);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,previous[index]);
            int width=index==4?95:256,height=index==4?95:radiance.height();
            check(GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH)==width
                && GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT)==height,"Compressed GPU table extent");
            float[] actual=new float[expected[index].length];
            GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_FLOAT,actual);
            check(Arrays.equals(actual,expected[index]),"Exact six-table run publication readback");
        }
        GL11.glBindTexture(GL11.GL_TEXTURE_2D,guardTexture);
        runBinding(previous,radiance.records(),guardTexture);
        failure[0]=12;
        try { publisher.publish(window,layout,radiance,epoch);throw new AssertionError("Partial run upload exposed"); }
        catch(IllegalStateException injected) { }
        check(publisher.ready(epoch)==0,"Failed run upload has no ready publication");
        for(int texture:previous)check(GL11.glIsTexture(texture),"Previous owned allocation retained after failed upload");
        for(int index=6;index<created.size();index++)check(!GL11.glIsTexture(created.get(index)),"Partial run allocation released");
        check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)==GL13.GL_TEXTURE2
            && GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==guardTexture
            && GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING)==guardBuffer,"Failed run upload restores binding/PBO state");
        for(int index=0;index<names.length;index++)check(GL11.glGetInteger(names[index])==values[index],"Run upload restores unpack state");
        failure[0]=-1;publisher.publish(window,layout,radiance,epoch);
        for(int texture:previous)check(!GL11.glIsTexture(texture),"Run replacement deletes old allocation");
        int[] latest=new int[6];for(int index=0;index<6;index++)latest[index]=publisher.texture(index,epoch);
        check(publisher.ready(new ReceiverRadianceVolume.Epoch(epoch.world(),2,1))==0,"Run GPU publication expires");
        publisher.close();publisher.close();
        for(int texture:latest)check(!GL11.glIsTexture(texture),"Run close releases all six textures");
        System.out.println("PASS NVIDIA six-texture run publication/readback, sixth-upload failure rollback, expiry/replacement/release and unpack/PBO restoration; not Minecraft sampler binding");
    }

    private static void runBinding(int[] textures,int records,int guardTexture) {
        int vertex=shader(GL20.GL_VERTEX_SHADER,"#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}");
        int fragment=shader(GL20.GL_FRAGMENT_SHADER,"""
            #version 330 compatibility
            uniform int aqualumenReceiverReady,aqualumenReceiverRunMode,aqualumenReceiverRunCount;
            uniform ivec3 aqualumenReceiverSize;
            uniform vec3 aqualumenReceiverOrigin;
            uniform sampler2D aqualumenReceiverCells,aqualumenReceiverSource,aqualumenReceiverSun,aqualumenReceiverFaces;
            uniform sampler2D aqualumenReceiverRunHeaders,aqualumenReceiverRunRanges;
            void main(){
                gl_FragColor=texture(aqualumenReceiverCells,vec2(0))+texture(aqualumenReceiverSource,vec2(0))
                    +texture(aqualumenReceiverSun,vec2(0))+texture(aqualumenReceiverFaces,vec2(0))
                    +texture(aqualumenReceiverRunHeaders,vec2(0))+texture(aqualumenReceiverRunRanges,vec2(0))
                    +vec4(vec3(aqualumenReceiverSize)+aqualumenReceiverOrigin,
                          float(aqualumenReceiverReady+aqualumenReceiverRunMode+aqualumenReceiverRunCount));
            }
            """);
        int program=GL20.glCreateProgram();GL20.glAttachShader(program,vertex);GL20.glAttachShader(program,fragment);GL20.glLinkProgram(program);
        check(GL20.glGetProgrami(program,GL20.GL_LINK_STATUS)!=0,GL20.glGetProgramInfoLog(program));
        GL20.glUseProgram(program);
        String[] names={"aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces",
            "aqualumenReceiverRunHeaders","aqualumenReceiverRunRanges"};
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        int[] before=new int[6];
        for(int index=0;index<6;index++) {
            GL20.glUniform1i(GL20.glGetUniformLocation(program,names[index]),7+index);
            GL13.glActiveTexture(GL13.GL_TEXTURE0+7+index);
            before[index]=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,guardTexture);
        }
        GL13.glActiveTexture(active);
        GL20.glUniform3i(GL20.glGetUniformLocation(program,"aqualumenReceiverSize"),7,8,9);
        GL20.glUniform3f(GL20.glGetUniformLocation(program,"aqualumenReceiverOrigin"),1,2,3);
        var binding=ReceiverTextureBinding.open(textures,new int[]{95,36,95},new float[]{-.5f,3.5f,4.5f},1,records);
        check(binding!=null && GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)==active,"Run bind preserves active texture");
        check(GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenReceiverReady"))==2
            && GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenReceiverRunMode"))==1
            && GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenReceiverRunCount"))==records,"Run binding sets ready/mode/count");
        int[] size=new int[3];float[] origin=new float[3];
        GL20.glGetUniformiv(program,GL20.glGetUniformLocation(program,"aqualumenReceiverSize"),size);
        GL20.glGetUniformfv(program,GL20.glGetUniformLocation(program,"aqualumenReceiverOrigin"),origin);
        check(Arrays.equals(size,new int[]{95,36,95}) && Arrays.equals(origin,new float[]{-.5f,3.5f,4.5f}),"Run binding sets bounds");
        for(int index=0;index<6;index++) {
            GL13.glActiveTexture(GL13.GL_TEXTURE0+7+index);
            check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==textures[index],"Six run sampler bindings match publication");
        }
        GL13.glActiveTexture(active);GL20.glUseProgram(0);rejects(binding::close);GL20.glUseProgram(program);
        binding.close();binding.close();
        GL20.glGetUniformiv(program,GL20.glGetUniformLocation(program,"aqualumenReceiverSize"),size);
        GL20.glGetUniformfv(program,GL20.glGetUniformLocation(program,"aqualumenReceiverOrigin"),origin);
        check(Arrays.equals(size,new int[]{7,8,9}) && Arrays.equals(origin,new float[]{1,2,3}),"Run close restores prior bounds");
        check(GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenReceiverReady"))==0
            && GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenReceiverRunMode"))==0
            && GL20.glGetUniformi(program,GL20.glGetUniformLocation(program,"aqualumenReceiverRunCount"))==0,"Run close restores prior readiness/mode/count");
        GL20.glUniform1i(GL20.glGetUniformLocation(program,names[4]),7);
        rejects(()->ReceiverTextureBinding.open(textures,new int[]{95,36,95},new float[]{0,0,0},1,records));
        GL20.glUniform1i(GL20.glGetUniformLocation(program,names[4]),11);
        int sampler=GL33.glGenSamplers();GL33.glSamplerParameteri(sampler,GL14.GL_TEXTURE_COMPARE_MODE,GL30.GL_COMPARE_REF_TO_TEXTURE);
        GL33.glBindSampler(7,sampler);
        rejects(()->ReceiverTextureBinding.open(textures,new int[]{95,36,95},new float[]{0,0,0},1,records));
        GL33.glBindSampler(7,0);GL33.glDeleteSamplers(sampler);
        for(int index=0;index<6;index++) {
            GL13.glActiveTexture(GL13.GL_TEXTURE0+7+index);
            check(GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D)==guardTexture,"Rejected binding leaves prior textures unchanged");
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,before[index]);
        }
        GL13.glActiveTexture(active);GL20.glUseProgram(0);
        GL20.glDeleteProgram(program);GL20.glDeleteShader(vertex);GL20.glDeleteShader(fragment);
        System.out.println("PASS NVIDIA compressed sampler/uniform bind and exact restoration, alias/comparison/program-owner controls; controlled context, not Minecraft scheduling or rendered appearance");
    }

    private static void lightingState(ReceiverRadianceTextureUpload uploader, ReceiverRadianceVolume.Epoch epoch,
                                      Thread owner, long window) {
        int vertex = shader(GL20.GL_VERTEX_SHADER, "#version 330 compatibility\nvoid main(){gl_Position=gl_Vertex;}");
        int fragment = shader(GL20.GL_FRAGMENT_SHADER, """
                #version 330 compatibility
                uniform mat4 gbufferModelViewInverse,shadowModelView,shadowProjection;
                uniform vec3 cameraPosition,sunPosition,shadowLightPosition;
                uniform float frameTimeCounter,rainStrength;
                uniform int aqualumenDimension;
                uniform sampler2D colortex6,colortex7;
                uniform sampler2DShadow shadowtex0;
                void main(){
                    vec4 position=gbufferModelViewInverse*shadowModelView*shadowProjection*vec4(gl_FragCoord.xyz,1);
                    vec3 light=cameraPosition+sunPosition+shadowLightPosition;
                    gl_FragColor=position+vec4(light,frameTimeCounter+rainStrength+float(aqualumenDimension))
                        +texture(colortex6,gl_FragCoord.xy)+texture(colortex7,gl_FragCoord.xy)
                        +vec4(texture(shadowtex0,gl_FragCoord.xyz));
                }
                """);
        int program = GL20.glCreateProgram();
        GL20.glAttachShader(program, vertex); GL20.glAttachShader(program, fragment); GL20.glLinkProgram(program);
        check(GL20.glGetProgrami(program, GL20.GL_LINK_STATUS) != 0, GL20.glGetProgramInfoLog(program));
        GL20.glUseProgram(program);
        float[] identity = {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
        for (String name : new String[]{"gbufferModelViewInverse", "shadowModelView", "shadowProjection"})
            GL20.glUniformMatrix4fv(GL20.glGetUniformLocation(program, name), false, identity);
        GL20.glUniform3f(GL20.glGetUniformLocation(program,"cameraPosition"),123,64,-27);
        GL20.glUniform3f(GL20.glGetUniformLocation(program,"sunPosition"),0,100,0);
        GL20.glUniform3f(GL20.glGetUniformLocation(program,"shadowLightPosition"),0,100,0);
        GL20.glUniform1f(GL20.glGetUniformLocation(program,"frameTimeCounter"),12);
        GL20.glUniform1f(GL20.glGetUniformLocation(program,"rainStrength"),.25f);
        int sky = uploader.create(2,3,new float[24]), clear = uploader.create(2,3,new float[24]);
        int shadow = GL11.glGenTextures();
        int active = GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE), unpack = GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING);
        GL13.glActiveTexture(GL13.GL_TEXTURE6); GL11.glBindTexture(GL11.GL_TEXTURE_2D, shadow);
        GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER,0);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL11.GL_DEPTH_COMPONENT,1,1,0,GL11.GL_DEPTH_COMPONENT,GL11.GL_FLOAT,0L);
        GL11.glTexParameteri(GL11.GL_TEXTURE_2D,GL14.GL_TEXTURE_COMPARE_MODE,GL30.GL_COMPARE_REF_TO_TEXTURE);
        GL15.glBindBuffer(GL21.GL_PIXEL_UNPACK_BUFFER,unpack);
        GL13.glActiveTexture(GL13.GL_TEXTURE4); GL11.glBindTexture(GL11.GL_TEXTURE_2D,sky);
        GL13.glActiveTexture(GL13.GL_TEXTURE5); GL11.glBindTexture(GL11.GL_TEXTURE_2D,clear);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"colortex6"),4);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"colortex7"),5);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"shadowtex0"),6);
        GL13.glActiveTexture(active);
        Runnable guard = () -> check(Thread.currentThread()==owner && GLFW.glfwGetCurrentContext()==window,"Lighting owner context");
        var state = ReceiverLightingState.capture(epoch,guard);
        check(state.program()==program && Arrays.equals(state.value("cameraPosition"),new float[]{123,64,-27}) &&
                Arrays.equals(state.value("shadowProjection"),identity) && state.value("rainStrength")[0]==.25f,"Actual uniform readback");
        check(state.texture("colortex6").texture()==sky && state.texture("colortex7").texture()==clear &&
                state.texture("shadowtex0").texture()==shadow,"Actual sampler binding readback");
        check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)==active && GL11.glGetInteger(GL21.GL_PIXEL_UNPACK_BUFFER_BINDING)==unpack &&
                GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM)==program,"Read-only lighting capture preserves GL state");
        float[] changed=state.value("cameraPosition"); changed[0]=0;
        check(state.value("cameraPosition")[0]==123 && state.current(epoch) &&
                !state.current(new ReceiverRadianceVolume.Epoch(epoch.world(),2,1)),"Owned values and frame expiry");
        int shadowSampler=GL33.glGenSamplers(); GL33.glBindSampler(6,shadowSampler);
        rejects(() -> ReceiverLightingState.capture(epoch,guard));
        GL33.glSamplerParameteri(shadowSampler,GL14.GL_TEXTURE_COMPARE_MODE,GL30.GL_COMPARE_REF_TO_TEXTURE);
        check(ReceiverLightingState.capture(epoch,guard).texture("shadowtex0").sampler()==shadowSampler,"Actual shadow sampler object overrides texture state");
        GL33.glBindSampler(6,0); GL33.glDeleteSamplers(shadowSampler);
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"colortex7"),4);
        rejects(() -> ReceiverLightingState.capture(epoch,guard));
        check(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE)==active,"Failed capture restores active unit");
        GL20.glUniform1i(GL20.glGetUniformLocation(program,"colortex7"),5);
        GL20.glUniform1f(GL20.glGetUniformLocation(program,"rainStrength"),Float.NaN);
        rejects(() -> ReceiverLightingState.capture(epoch,guard));
        GL20.glUseProgram(0); rejects(() -> ReceiverLightingState.capture(epoch,guard));
        for(int unit=4;unit<=6;unit++){GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);GL11.glBindTexture(GL11.GL_TEXTURE_2D,0);}
        GL13.glActiveTexture(active);
        uploader.delete(sky); uploader.delete(clear); uploader.delete(shadow);
        GL20.glDeleteProgram(program); GL20.glDeleteShader(vertex); GL20.glDeleteShader(fragment);
        System.out.println("PASS actual GL lighting binding/uniform capture, shadow sampler override, alias/nonfinite/missing-owner rejection, owned values and epoch expiry; borrowed textures, not Iris scheduling or source production");
    }

    private static int shader(int type, String source) {
        int shader = GL20.glCreateShader(type); GL20.glShaderSource(shader,source); GL20.glCompileShader(shader);
        check(GL20.glGetShaderi(shader,GL20.GL_COMPILE_STATUS)!=0,GL20.glGetShaderInfoLog(shader));
        return shader;
    }

    private static void rejects(Runnable action) {
        try { action.run(); } catch (IllegalStateException expected) { return; }
        throw new AssertionError("Unqualified lighting state accepted");
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
