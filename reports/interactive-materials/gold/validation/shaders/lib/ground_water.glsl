// The last two rows of the face atlas hold 1,024 columns of water boundary
// cells, cleared with the shadow capture each frame. Using a bit per height
// lets a dry bank sit beside water without borrowing a neighbouring column.
ivec2 groundWaterColumn(ivec3 cell) {
    ivec2 q=cell.xz-bounceOrigin().xz;
    int index=q.x+32*q.y;
    return ivec2(index%768,256+index/768);
}
uint groundWaterMask(ivec3 cell) {
    if(!bounceContains(cell) || imageSize(bounceSurfaceImage).y<258) return 0u;
    return imageLoad(bounceSurfaceImage,groundWaterColumn(cell)).r >> uint(cell.y-bounceOrigin().y);
}
