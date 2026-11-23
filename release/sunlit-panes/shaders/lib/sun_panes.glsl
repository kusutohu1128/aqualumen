// The same captured panes that tint local lamps can filter the direct solar
// term. Opaque and entity shadow-map visibility is still evaluated separately.
vec3 sunPaneTransmission(vec3 position, vec3 normal, vec3 sun) {
    const int indexRow = 15008;
    if (texelFetch(aqualumenLightField, ivec2(0, indexRow), 0).r < .5)
        return vec3(1);

    vec3 eye = lampGridPosition(vec3(0), cameraPosition);
    vec3 start = eye + position + normal * .001;
    float enter = 0., leave = 1e20;
    for (int axis = 0; axis < 3; ++axis) {
        if (abs(sun[axis]) < 1e-7) {
            if (start[axis] < 0. || start[axis] >= 64.) return vec3(1);
        } else {
            float a = -start[axis] / sun[axis];
            float b = (64. - start[axis]) / sun[axis];
            enter = max(enter, min(a,b));
            leave = min(leave, max(a,b));
        }
    }

    // An empty eight-block tile costs one step. A line can cross at most
    // 192 voxel planes inside this grid, including simultaneous crossings.
    vec3 trans = vec3(1);
    for (int stepIndex = 0; stepIndex < 193 && enter < leave; ++stepIndex) {
        ivec3 cell = ivec3(floor(start + sun * (enter + .0001)));
        if (!lampInGrid(cell)) break;
        ivec3 tile = cell / 8;
        int row = int(texelFetch(aqualumenLightField, ivec2(1 + tile.y*8 + tile.z, indexRow), 0).r);
        bool occupied = (row & (1 << tile.x)) != 0;
        int width = occupied ? 1 : 8;
        vec3 boundary = vec3((cell / width) * width) + step(vec3(0),sun) * float(width);
        float end = leave;
        for (int axis = 0; axis < 3; ++axis) {
            if (abs(sun[axis]) >= 1e-7)
                end = min(end, (boundary[axis] - start[axis]) / sun[axis]);
        }
        if (occupied) {
            int word = int(texelFetch(aqualumenLightField, lampCellAddress(cell), 0).r);
            int shape = word & 63;
            if (shape >= 32 && shape < 48) {
                vec3 toEye = abs(vec3(cell) + .5 - eye);
                float coverage = 1. - smoothstep(18., 23., max(toEye.x,max(toEye.y,toEye.z)));
                float travel = max(0., end - enter);
                float lengthInPane = paneDistance((word >> 6) & 15,
                    (start + sun*enter - vec3(cell)).xz, sun.xz*travel, travel);
                trans *= pow(lampGlass(shape-32), vec3(lengthInPane*coverage));
            }
        }
        enter = end;
    }
    return trans;
}
