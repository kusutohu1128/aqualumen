from pathlib import Path
import struct
p=Path(__file__).resolve().parent
src=(p/'grate_capture.glsl').read_text().replace('(gl_TextureMatrix[0]*vec4(mc_midTexCoord,0,1)).xy','vec2(.5)')
header="""#version 450
layout(local_size_x=1) in;
layout(binding=1) uniform sampler2D gtexture;
layout(binding=0,r32ui) uniform coherent uimage2D doorMaskImage;
layout(binding=1,r32ui) uniform coherent uimage2D lampCellImage;
ivec2 lampCellAddress(ivec3 cell){return cell.xy;}
"""
main="""
void main(){
 uint index=gl_GlobalInvocationID.x;
 vec3 normal=vec3(0.0);
 normal[int(index)/2]=(index&1u)==0u?-1.:1.;
 captureGrate(ivec3(0),0,normal,vec2(0));
}
"""
(p/'capture-test.comp').write_text(header+src+main)
code=(p/'probe.cpp').read_text().replace('"probe.comp"','"capture-test.comp"')
i=code.index(' GLuint buf;')
code=code[:i]+"""
 // Use the independently generated default-alpha table as an RGBA atlas,
 // then check that shader-side capture reconstructs every one of its rows.
 std::vector<unsigned> atlas(256);
 for(int y=0;y<16;y++)for(int x=0;x<16;x++)atlas[y*16+x]=(mask[105*16+y]&(1u<<x))?0xffffffffu:0xffffffu;
 std::vector<unsigned> zero(16*120);
 glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,120,GL_RED_INTEGER,GL_UNSIGNED_INT,zero.data());
 glBindImageTexture(0,tex,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
 GLuint cells;glGenTextures(1,&cells);glBindTexture(GL_TEXTURE_2D,cells);glTexStorage2D(GL_TEXTURE_2D,1,GL_R32UI,1,1);
 glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1,1,GL_RED_INTEGER,GL_UNSIGNED_INT,zero.data());
 glBindImageTexture(1,cells,0,GL_FALSE,0,GL_READ_WRITE,GL_R32UI);
 GLuint srcTex;glGenTextures(1,&srcTex);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,srcTex);glTexStorage2D(GL_TEXTURE_2D,1,GL_RGBA8,16,16);
 glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
 glTexSubImage2D(GL_TEXTURE_2D,0,0,0,16,16,GL_RGBA,GL_UNSIGNED_BYTE,atlas.data());
 glDispatchCompute(6,1,1);glMemoryBarrier(GL_TEXTURE_UPDATE_BARRIER_BIT);
 glBindTexture(GL_TEXTURE_2D,cells);GLuint word;glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,&word);
 glBindTexture(GL_TEXTURE_2D,tex);glGetTexImage(GL_TEXTURE_2D,0,GL_RED_INTEGER,GL_UNSIGNED_INT,zero.data());
 bool pass=glGetError()==GL_NO_ERROR && zero==mask && word==(11u|(63u<<9u));
 std::cout<<(pass?"PASS":"FAIL")<<" atlas capture, orientation face bits, untouched door and leaf slots; word="<<word<<"\\n";return pass?0:1;
}"""
(p/'capture-test.cpp').write_text(code)
