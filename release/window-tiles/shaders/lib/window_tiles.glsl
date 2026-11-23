// Divide the current viewport at integer pixel boundaries, also at odd sizes.
const ivec2 windowTileCount=ivec2(16,9);
ivec2 windowTileAddress(ivec2 tile) {
    int i=tile.x+windowTileCount.x*tile.y;
    int index=32*(16+i/8)+23+i%8;
    return ivec2(index%512,2688+index/512);
}
