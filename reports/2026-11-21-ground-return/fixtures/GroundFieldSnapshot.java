package dev.aqualumen.bench;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.*;

// Read after the frame-sampling interval in the isolated, UUID-checked forest.
// These dimensions and formats identify private pack textures uniquely.
final class GroundFieldSnapshot {
    private static int texture(int width,int height,int format) throws Exception {
        var gl=Class.forName("org.lwjgl.opengl.GL45");
        var test=Class.forName("org.lwjgl.opengl.GL11").getMethod("glIsTexture",int.class);
        var attr=gl.getMethod("glGetTextureLevelParameteri",int.class,int.class,int.class);
        int found=0;
        for(int id=1;id<=4096;id++) {
            if(!(Boolean)test.invoke(null,id)) continue;
            if((int)attr.invoke(null,id,0,0x1000)!=width || (int)attr.invoke(null,id,0,0x1001)!=height ||
               (int)attr.invoke(null,id,0,0x1003)!=format) continue;
            if(found!=0) throw new IllegalStateException("Ambiguous ground field "+width+"x"+height);
            found=id;
        }
        if(found==0) throw new IllegalStateException("Missing ground field "+width+"x"+height);
        return found;
    }
    static Map<String,Object> read(double[] eye) throws Exception {
        int field=texture(1536,1536,0x881a),pigments=texture(768,258,0x8236);
        var gl=Class.forName("org.lwjgl.opengl.GL45");
        var get=Class.forName("org.lwjgl.opengl.GL11").getMethod("glGetInteger",int.class);
        for(int state:new int[]{0x88ed,0x0d02,0x0d03,0x0d04,0x806b,0x806c})
            if((int)get.invoke(null,state)!=0) throw new IllegalStateException("Unexpected pixel-pack state");
        var pixel=gl.getMethod("glGetTextureSubImage",int.class,int.class,int.class,int.class,int.class,
            int.class,int.class,int.class,int.class,int.class,ByteBuffer.class);
        var data=ByteBuffer.allocateDirect(64).order(ByteOrder.nativeOrder());
        Map<String,Object> rows=new LinkedHashMap<>();
        // All floor tiles, including unchanged natural cells, plus the north birch face.
        for(int y:new int[]{64,65,66}) for(int z=354;z<=360;z++) for(int x=206;x<=212;x++) {
            boolean trunk=x==209 && z==360;
            if(!trunk && (z==360 || y!=64)) continue;
            int u=(x-8*(int)Math.floor(eye[0]/8)+16)&31;
            int v=(y-8*(int)Math.floor(eye[1]/8)+16)&31;
            int w=(z-8*(int)Math.floor(eye[2]/8)+16)&31;
            int index=6*(u+32*(w+32*v))+(trunk?4:3), a=index%768,b=index/768;
            pixel.invoke(null,pigments,0,a,b,0,1,1,1,0x8d94,0x1405,data);
            int word=data.getInt(0);
            pixel.invoke(null,field,0,2*a,(trunk?1024:512)+2*b,0,2,2,1,0x1908,0x1406,data);
            List<List<Float>> samples=new ArrayList<>();
            for(int i=0;i<4;i++) samples.add(List.of(data.getFloat(i*16),data.getFloat(i*16+4),
                data.getFloat(i*16+8),data.getFloat(i*16+12)));
            rows.put(x+","+y+","+z,Map.of("rgb8",List.of(word&255,(word>>8)&255,(word>>16)&255),
                "captured",(word&0x80000000)!=0,"quarterRGBA",samples));
        }
        return rows;
    }
}
