// A 64 m window of one-metre world cells uses a toroidal address. The
// absolute anchor in each tile distinguishes two different laps of the ring.
ivec3 openTileOrigin() { return ivec3(floor(cameraPosition/8.))-4; }
ivec3 openRingTile(ivec3 tile) { return (openTileOrigin()+tile)&ivec3(7); }
ivec2 openTag(int row,int slot) { return ivec2(0,2688)+lampAddress(row*32+slot,512); }
ivec2 openCellAddress(ivec3 cell) {
    ivec3 ringCell=(cell+(openTileOrigin()&ivec3(7))*8)&ivec3(63);
    return ivec2(0,2112)+lampCellAddress(ringCell);
}
