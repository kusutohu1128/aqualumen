    // One centre sample per actual leaf face, stored in its first quarter.
    // Keep alpha zero so no other pass interprets this as an opaque reflector.
    if(LOCAL_BOUNCE==1 && i==0 && (surface&0xc0000000u)==0x40000000u && bounceCoverage(centre-eye)>0. &&
       texelFetch(aqualumenLightList,ivec2(0,row),0).r>0.) {
        uint word=uint(texelFetch(aqualumenLightField,lampCellAddress(cell),0).r);
        int slot=int((word>>6u)&63u);
        if((word&63u)==2u && slot>0 && slot<=32) {
            vec4 sprite=unpackUnorm4x8(texelFetch(aqualumenDoorMask,ivec2(1,38+2*slot),0).r);
            vec3 leafRho=pow(unpackUnorm4x8(surface).rgb*sprite.rgb,vec3(2.2));
            vec3 reflected,transmitted;
            vec4 unusedArea;
            if(sprite.a>0.) outgoing=leafRho*sprite.a*bounceCoverage(centre-eye)*
                lampAndLavaLighting(centre-eye,n,vec3(0),0.,0.,false,0.,false,leafSurfaceNone(),
                                    reflected,transmitted,unusedArea,false);
        }
    }
