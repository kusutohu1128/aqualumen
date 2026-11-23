    for(int by=firstBrick.y;by<=lastBrick.y;by++) {
        vec2 yWindow=torchBrickWindow(start.y,delta.y,extent.y,by);
        if(yWindow.x>yWindow.y) continue;
        ivec2 zs=torchBrickRange(start.z,delta.z,extent.z,yWindow,firstBrick.z,lastBrick.z);
        for(int bz=zs.x;bz<=zs.y;bz++) {
            vec2 zWindow=torchBrickWindow(start.z,delta.z,extent.z,bz);
            vec2 yzWindow=vec2(max(yWindow.x,zWindow.x),min(yWindow.y,zWindow.y));
            if(yzWindow.x>yzWindow.y) continue;
            ivec2 xs=torchBrickRange(start.x,delta.x,extent.x,yzWindow,firstBrick.x,lastBrick.x);
            for(int bx=xs.x;bx<=xs.y;bx++) {
        ivec3 tile=ivec3(bx,by,bz);
