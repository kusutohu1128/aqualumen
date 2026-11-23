#version 330 compatibility
uniform usampler2D aqualumenRawIndex;
flat out int capturedLava;
out vec2 texcoord;
void main() {
    gl_Position=ftransform();
    texcoord=gl_MultiTexCoord0.xy;
    // Capture sets this bit for any lava in the entire grid, including offscreen emitters.
    capturedLava=1;
    if (textureSize(aqualumenRawIndex,0)==ivec2(128,1801))
        capturedLava=int(texelFetch(aqualumenRawIndex,ivec2(0,72),0).r!=0u);
}
