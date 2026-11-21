package dev.aqualumen.physics;

import java.nio.ByteBuffer;
import java.util.*;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL13;
import org.lwjgl.opengl.GL15;
import org.lwjgl.system.MemoryUtil;

/** TEST-only actual atlas readback. Raw binding changes are restored before returning. */
final class GpuReceiverAtlas {
    private GpuReceiverAtlas() {}
    private static final int PACK_BUFFER=0x88eb,UNPACK_BUFFER=0x88ec;
    private static final int[] PACK={GL11.GL_PACK_ALIGNMENT,GL11.GL_PACK_ROW_LENGTH,GL11.GL_PACK_SKIP_ROWS,
            GL11.GL_PACK_SKIP_PIXELS,GL11.GL_PACK_SWAP_BYTES,GL11.GL_PACK_LSB_FIRST,0x806b,0x806c};
    private static final int[] UNPACK={GL11.GL_UNPACK_ALIGNMENT,GL11.GL_UNPACK_ROW_LENGTH,GL11.GL_UNPACK_SKIP_ROWS,
            GL11.GL_UNPACK_SKIP_PIXELS,GL11.GL_UNPACK_SWAP_BYTES,GL11.GL_UNPACK_LSB_FIRST,0x806d,0x806e};
    private record State(int active,int texture,int packBuffer,int unpackBuffer,List<Integer> pack,List<Integer> unpack) {
        static State read() {
            var pack=new ArrayList<Integer>();var unpack=new ArrayList<Integer>();
            for(int name:PACK)pack.add(GL11.glGetInteger(name));for(int name:UNPACK)unpack.add(GL11.glGetInteger(name));
            return new State(GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE),GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D),
                    GL11.glGetInteger(0x88ed),GL11.glGetInteger(0x88ef),pack,unpack);
        }
        void restore() {
            GL13.glActiveTexture(active);GL11.glBindTexture(GL11.GL_TEXTURE_2D,texture);
            for(int i=0;i<PACK.length;i++)GL11.glPixelStorei(PACK[i],pack.get(i));
            for(int i=0;i<UNPACK.length;i++)GL11.glPixelStorei(UNPACK[i],unpack.get(i));
            GL15.glBindBuffer(PACK_BUFFER,packBuffer);GL15.glBindBuffer(UNPACK_BUFFER,unpackBuffer);
        }
        Map<String,Object> json() {return Map.of("activeTexture",active,"texture2D",texture,"packBuffer",packBuffer,
                "unpackBuffer",unpackBuffer,"packValues",pack,"unpackValues",unpack);}
    }
    private static void tight(int[] names,int target) {
        GL15.glBindBuffer(target,0);
        for(int name:names)GL11.glPixelStorei(name,name==GL11.GL_PACK_ALIGNMENT || name==GL11.GL_UNPACK_ALIGNMENT?1:0);
    }
    private static ReceiverAtlas.Snapshot read(int width,int height) {
        if(width<1 || height<1 || width>2048 || height>2048)throw new IllegalStateException("GPU atlas shape exceeds bounded capture");
        ByteBuffer bytes=MemoryUtil.memAlloc(width*height*4);
        try {
            tight(PACK,PACK_BUFFER);GL11.glGetTexImage(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,bytes);
            byte[] copy=new byte[bytes.remaining()];bytes.get(copy);
            var snapshot=ReceiverAtlas.capture(width,height,copy);
            if(snapshot==null)throw new IllegalStateException("Actual atlas copy unready");return snapshot;
        } finally {MemoryUtil.memFree(bytes);}
    }
    record Capture(ReceiverAtlas.Snapshot pixels,Map<String,Object> metadata) {}
    static Capture capture(Object client) throws Exception {
        if(!(boolean)Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread").invoke(null))
            throw new IllegalStateException("Atlas observation outside render thread");
        Object manager=client.getClass().getMethod("method_1531").invoke(client);
        Class<?> managerType=Class.forName("net.minecraft.class_1060"),atlasType=Class.forName("net.minecraft.class_1059");
        var field=managerType.getDeclaredField("field_5286");field.setAccessible(true);
        Object identifier=atlasType.getField("field_5275").get(null);
        Object texture=((Map<?,?>)field.get(manager)).get(identifier);
        if(!atlasType.isInstance(texture) || !identifier.equals(atlasType.getMethod("method_24106").invoke(texture)))
            throw new IllegalStateException("Already-loaded block atlas not registered");
        var idField=Class.forName("net.minecraft.class_1044").getDeclaredField("field_5204");idField.setAccessible(true);
        int id=idField.getInt(texture);
        if(id<=0 || !GL11.glIsTexture(id))throw new IllegalStateException("Existing block atlas GL identity invalid");
        State before=State.read();ReceiverAtlas.Snapshot pixels;var metadata=new LinkedHashMap<String,Object>();
        try {
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,id);
            int width=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH);
            int height=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT);
            int format=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_INTERNAL_FORMAT);
            int[] bits=new int[4],types=new int[4];
            int[] bitEnums={0x805c,0x805d,0x805e,0x805f},typeEnums={0x8c10,0x8c11,0x8c12,0x8c13};
            for(int i=0;i<4;i++) {
                bits[i]=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,bitEnums[i]);
                types[i]=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,typeEnums[i]);
            }
            if(!ReceiverAtlas.rgba8Storage(format,bits,types))throw new IllegalStateException("Unqualified actual atlas format/bits/types: "+format+"/"+Arrays.toString(bits)+"/"+Arrays.toString(types));
            metadata.put("atlas","minecraft:textures/atlas/blocks.png");metadata.put("textureID",id);
            metadata.put("size",List.of(width,height));metadata.put("internalFormat",format);
            metadata.put("componentBits",Arrays.stream(bits).boxed().toList());metadata.put("componentTypes",Arrays.stream(types).boxed().toList());
            metadata.put("minFilter",GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MIN_FILTER));
            metadata.put("magFilter",GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_MAG_FILTER));
            metadata.put("wrapS",GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_WRAP_S));
            metadata.put("wrapT",GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL11.GL_TEXTURE_WRAP_T));
            metadata.put("baseLevel",GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,0x813c));
            metadata.put("maxLevel",GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,0x813d));
            pixels=read(width,height);
            if(idField.getInt(texture)!=id || ((Map<?,?>)field.get(manager)).get(identifier)!=texture)
                throw new IllegalStateException("Atlas identity changed during one-shot observation");
        } finally {before.restore();}
        State after=State.read();if(!after.equals(before))throw new IllegalStateException("Actual atlas GL state restoration failed");
        metadata.put("before",before.json());metadata.put("after",after.json());metadata.put("listedGLStateRestored",true);
        metadata.put("textureDataMutated",false);metadata.put("actualTerrainSamplerBindingProven",false);
        metadata.put("filteredTextureFetchProven",false);metadata.put("atlasReloadCoherenceProven",false);
        return new Capture(pixels,metadata);
    }
    static Map<String,Object> calibration() throws Exception {
        State before=State.read();int id=GL11.glGenTextures();ReceiverTexture.Snapshot snapshot;
        var sprite=new ReceiverFace.Sprite("fixture","GPU_known_RGBA",0,1,0,1);
        var face=new ReceiverFace.Face(1,1,sprite,new ReceiverFace.UV(0,0),new ReceiverFace.UV(0,1),new ReceiverFace.UV(1,0),
                new ReceiverFace.Color(1,1,1),new ReceiverFace.Color(1,1,1),true,15,0,1);
        ByteBuffer bytes=MemoryUtil.memAlloc(16);
        try {
            GL11.glBindTexture(GL11.GL_TEXTURE_2D,id);tight(UNPACK,UNPACK_BUFFER);
            for(int i=0;i<4;i++)bytes.put((byte)(i*3+1)).put((byte)(i*3+2)).put((byte)(i*3+3)).put((byte)255);
            bytes.flip();GL11.glTexImage2D(GL11.GL_TEXTURE_2D,0,GL11.GL_RGBA8,2,2,0,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,bytes);
            snapshot=read(2,2).sprite(sprite,2,2);
            bytes.clear();bytes.putInt(-1).flip();
            GL11.glTexSubImage2D(GL11.GL_TEXTURE_2D,0,0,1,1,1,GL11.GL_RGBA,GL11.GL_UNSIGNED_BYTE,bytes);
            var mutated=read(2,2).sprite(sprite,2,2);
            if(snapshot==null || !snapshot.sample(face,.75,.25).equals(new ReceiverTexture.Sample(0,1,7,8,9,255))
                    || mutated==null || !mutated.sample(face,.75,.25).equals(new ReceiverTexture.Sample(0,1,255,255,255,255))
                    || !snapshot.rgbaSHA256().equals("60095e8c93bdb6d7cd09508d4410ce5b24f669de72bbd064f26bd67152fd5be1"))
                throw new IllegalStateException("Actual GPU known texture channel/orientation/ownership control failed");
        } finally {MemoryUtil.memFree(bytes);GL11.glDeleteTextures(id);before.restore();}
        if(!State.read().equals(before))throw new IllegalStateException("Owned GPU control did not restore state");
        return Map.of("expectedRGBA",List.of(7,8,9,255),"rgbaSHA256",snapshot.rgbaSHA256(),
                "ownGPUTextureMutationReadbackRGBA",List.of(255,255,255,255),
                "immutableAfterOwnGPUTextureMutation",true,"actualAssetMutated",false,"listedGLStateRestored",true,
                "before",before.json(),"after",State.read().json());
    }
}
