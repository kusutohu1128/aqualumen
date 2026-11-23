#ifdef WET_OAK_COMPONENTS
    vec3 sampleWorld=position+cameraPosition;
    if(normal.y>.99 && abs(sampleWorld.y-64.)<.01 && all(greaterThanEqual(sampleWorld.xz,vec2(570,419))) && all(lessThan(sampleWorld.xz,vec2(572,421))) && !pendingAreaLight) {
        vec3 Y=vec3(.2126,.7152,.0722);
        vec3 clearFilm,clearThrough;
        bool savedPending=pendingAreaLight;
        wetSkipOwner=true;
        vec3 clearBlock=lampLighting(position,normal,view,roughness,lightmap.x,false,reflected.a,film>0.,leaf,clearFilm,clearThrough);
        wetSkipOwner=false;
        pendingAreaLight=savedPending;
        wetComponents=vec4(dot(albedo*(block-reflected.rgb),Y),dot(albedo*reflected.rgb,Y),dot(film*lampFilm,Y),
                           1.+dot(albedo*(clearBlock+reflected.rgb)+film*clearFilm,Y));
    }
#endif
