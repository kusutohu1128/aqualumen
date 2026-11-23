    // The solid-valid bit stays clear. Only the lamp-return emitter pass uses
    // this actual mesh face's biome tint. The sprite and coverage are published
    // after shadow capture by the existing cutout-mask table.
    if(id==10300) {
        ivec3 leafCell=ivec3(floor(lampGridPosition(position+offset,cameraPosition)));
        if(bounceContains(leafCell) && imageSize(bounceSurfaceImage).x==768) {
            ivec2 address=bounceAddress(leafCell,2*axis+int(normal[axis]>0.));
            uint tint=packUnorm4x8(vec4(clamp(gl_Color.rgb,0.,1.),0));
            imageAtomicMax(bounceSurfaceImage,address,0x40000000u|tint);
        }
        return;
    }
#ifdef LOCAL_CUTOUT
    return;
#endif
