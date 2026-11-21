package dev.aqualumen.physics;

import java.util.Objects;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL13;
import org.lwjgl.opengl.GL14;
import org.lwjgl.opengl.GL20;
import org.lwjgl.opengl.GL30;
import org.lwjgl.opengl.GL33;
import org.lwjgl.opengl.GL;

public final class ReceiverTerrainState {
    private final ReceiverRadianceVolume.Epoch epoch;
    private final int program, atlas, sampler, width, height;
    private final ReceiverVertexShader.Uniforms uniforms;

    private ReceiverTerrainState(ReceiverRadianceVolume.Epoch epoch, int program, int atlas,
                                 int sampler, int width, int height, ReceiverVertexShader.Uniforms uniforms) {
        this.epoch=epoch; this.program=program; this.atlas=atlas; this.sampler=sampler;
        this.width=width; this.height=height; this.uniforms=uniforms;
    }

    public static ReceiverTerrainState capture(ReceiverRadianceVolume.Epoch epoch) {
        Objects.requireNonNull(epoch);
        int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if(program==0 || GL20.glGetUniformLocation(program,"iris_LightmapTextureMatrix")<0
                || GL20.glGetUniformLocation(program,"u_TexCoordShrink")<0) return null;
        int count=GL20.glGetProgrami(program,GL20.GL_ATTACHED_SHADERS);
        if(count<1 || count>8) return null;
        int[] shaders=new int[count], length=new int[1];
        GL20.glGetAttachedShaders(program,length,shaders);
        boolean terrain=false;
        for(int shader:shaders) {
            if(GL20.glGetShaderi(shader,GL20.GL_SHADER_TYPE)!=GL20.GL_FRAGMENT_SHADER) continue;
            int size=GL20.glGetShaderi(shader,GL20.GL_SHADER_SOURCE_LENGTH);
            if(size<1 || size>262144) return null;
            String source=GL20.glGetShaderSource(shader);
            terrain=source.contains("terrainLight") && source.contains("vertexColor.a") && !source.contains("refractionTrace");
        }
        if(!terrain) return null;
        float[] matrix=uniform(program,"iris_LightmapTextureMatrix",16);
        float[] shrink=uniform(program,"u_TexCoordShrink",2);
        var uniforms=ReceiverVertexShader.Uniforms.capture(matrix,shrink);
        if(uniforms==null || shrink[0]<0 || shrink[1]<0 || shrink[0]>1 || shrink[1]>1)
            throw new IllegalStateException("Terrain UV/lightmap uniforms unavailable");
        int location=GL20.glGetUniformLocation(program,"gtexture");
        if(location<0) throw new IllegalStateException("Terrain atlas sampler unavailable");
        int unit=GL20.glGetUniformi(program,location);
        if(unit<0 || unit>=GL11.glGetInteger(GL20.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS))
            throw new IllegalStateException("Terrain atlas unit invalid");
        int active=GL11.glGetInteger(GL13.GL_ACTIVE_TEXTURE);
        try {
            GL13.glActiveTexture(GL13.GL_TEXTURE0+unit);
            int atlas=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
            if(atlas==0 || !GL11.glIsTexture(atlas)) throw new IllegalStateException("Terrain atlas is unbound");
            int width=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH);
            int height=GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT);
            int sampler=GL.getCapabilities().OpenGL33 || GL.getCapabilities().GL_ARB_sampler_objects
                    ? GL30.glGetIntegeri(GL33.GL_SAMPLER_BINDING,unit) : 0;
            int compare=sampler==0 ? GL11.glGetTexParameteri(GL11.GL_TEXTURE_2D,GL14.GL_TEXTURE_COMPARE_MODE)
                    : GL33.glGetSamplerParameteri(sampler,GL14.GL_TEXTURE_COMPARE_MODE);
            if(width<1 || height<1 || compare!=GL11.GL_NONE) throw new IllegalStateException("Terrain atlas storage/comparison invalid");
            return new ReceiverTerrainState(epoch,program,atlas,sampler,width,height,uniforms);
        } finally { GL13.glActiveTexture(active); }
    }

    private static float[] uniform(int program,String name,int count) {
        float[] values=new float[count];
        GL20.glGetUniformfv(program,GL20.glGetUniformLocation(program,name),values);
        for(float value:values) if(!Float.isFinite(value)) throw new IllegalStateException("Nonfinite terrain uniform");
        return values;
    }

    public ReceiverTriangle.Quad decode(ReceiverSodiumScope.Snapshot source) {
        if(source==null || source.epoch().world()!=epoch.world() || source.epoch().frame()!=epoch.frame()
                || source.epoch().resources()!=epoch.resources() || source.packed().size()!=4) return null;
        var vertices=new ReceiverTriangle.Vertex[4];
        for(int index=0;index<4;index++) {
            var raw=source.raw().get(index);
            var decoded=ReceiverVertexShader.decode(source.packed().get(index),uniforms);
            if(decoded==null || decoded.u()<0 || decoded.u()>1 || decoded.v()<0 || decoded.v()>1) return null;
            vertices[index]=new ReceiverTriangle.Vertex(raw.x()-Math.floorMod(source.x(),16),
                    raw.z()-Math.floorMod(source.z(),16),decoded);
        }
        return ReceiverTriangle.capture(vertices,new int[]{0,1,2,2,3,0});
    }

    public String description() {
        return "program="+program+" atlas="+atlas+" sampler="+sampler+" size="+width+"x"+height;
    }
    public java.util.List<ReceiverQuadIntersection.Quad> decodeGeometry(ReceiverSodiumScope.GeometrySnapshot source,
                                                                     ReceiverQuadIntersection.Alpha alpha) {
        Objects.requireNonNull(alpha);
        if (source == null || source.epoch().world() != epoch.world() || source.epoch().frame() != epoch.frame()
                || source.epoch().resources() != epoch.resources()) return null;
        var quads = new java.util.ArrayList<ReceiverQuadIntersection.Quad>();
        for (var face : source.faces()) {
            if (face.packed().size() != 4) return null;
            var points = new ReceiverQuadIntersection.Point[4];
            for (int index = 0; index < 4; index++) {
                var raw = face.raw().get(index);
                var decoded = ReceiverVertexShader.decode(face.packed().get(index),uniforms);
                if (decoded == null || decoded.u() < 0 || decoded.u() > 1 || decoded.v() < 0 || decoded.v() > 1) return null;
                points[index] = new ReceiverQuadIntersection.Point(source.x()+(double)raw.x()-face.offsetX(),
                        source.y()+(double)raw.y()-face.offsetY(),source.z()+(double)raw.z()-face.offsetZ(),decoded.u(),decoded.v());
            }
            quads.add(new ReceiverQuadIntersection.Quad(points[0],points[1],points[2],points[3],alpha));
        }
        return java.util.List.copyOf(quads);
    }
    public int atlas() { return atlas; }
    public java.util.List<ReceiverMaterialTriangle> decodeMaterialGeometry(ReceiverSodiumScope.GeometrySnapshot source) {
        if(source==null || !source.epoch().matches(epoch.world(),epoch.frame(),epoch.resources()))return null;
        var triangles=new java.util.ArrayList<ReceiverMaterialTriangle>();
        try {
            for(var face:source.faces()) {
                if(face.packed().size()!=4)return null;
                var vertices=new ReceiverMaterialTriangle.Vertex[4];
                for(int index=0;index<4;index++) {
                    var decoded=ReceiverVertexShader.decode(face.packed().get(index),uniforms);
                    if(decoded==null)return null;
                    var raw=face.raw().get(index);
                    vertices[index]=new ReceiverMaterialTriangle.Vertex(source.x()+(double)raw.x()-face.offsetX(),
                            source.y()+(double)raw.y()-face.offsetY(),source.z()+(double)raw.z()-face.offsetZ(),decoded);
                }
                triangles.add(new ReceiverMaterialTriangle(epoch,vertices[0],vertices[1],vertices[2]));
                triangles.add(new ReceiverMaterialTriangle(epoch,vertices[0],vertices[2],vertices[3]));
            }
        } catch(IllegalArgumentException error) {return null;}
        return java.util.List.copyOf(triangles);
    }
    public int sampler() { return sampler; }
}
