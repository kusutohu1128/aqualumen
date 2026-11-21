package dev.aqualumen.physics;

import java.util.HashSet;
import java.util.Set;

public final class ReceiverPlantProbe {
    private static boolean attempted;
    private static final Set<String> plants = Set.of("minecraft:seagrass","minecraft:tall_seagrass",
            "minecraft:kelp","minecraft:kelp_plant");
    private ReceiverPlantProbe() {}

    public static void capture(ReceiverRadianceVolume.Epoch epoch, int centerX, int top, int centerZ, ReceiverTerrainState terrain,
                               ReceiverLightingState lighting)
            throws ReflectiveOperationException {
        capture(epoch,centerX,top,centerZ,terrain,lighting,null);
    }
    public static void capture(ReceiverRadianceVolume.Epoch epoch, int centerX, int top, int centerZ, ReceiverTerrainState terrain,
                               ReceiverLightingState lighting,ReceiverRunPublisher.Window requestedWindow)
            throws ReflectiveOperationException {
        if (attempted) return;
        attempted = true;
        var atlas = ReceiverAtlasReadback.capture(terrain.atlas(),terrain.sampler());
        ReceiverAtlasAlpha.Filter filter = switch (atlas.minFilter()) {
            case org.lwjgl.opengl.GL11.GL_NEAREST, org.lwjgl.opengl.GL11.GL_NEAREST_MIPMAP_NEAREST,
                    org.lwjgl.opengl.GL11.GL_NEAREST_MIPMAP_LINEAR -> ReceiverAtlasAlpha.Filter.NEAREST;
            case org.lwjgl.opengl.GL11.GL_LINEAR, org.lwjgl.opengl.GL11.GL_LINEAR_MIPMAP_NEAREST,
                    org.lwjgl.opengl.GL11.GL_LINEAR_MIPMAP_LINEAR -> ReceiverAtlasAlpha.Filter.LINEAR;
            default -> throw new IllegalStateException("Unsupported atlas filter");
        };
        var wrapU = wrap(atlas.wrapU());
        var wrapV = wrap(atlas.wrapV());
        System.out.println("[Aqualumen Receiver] plant-atlas-captured frame="+epoch.frame()+" resources="+epoch.resources()+
                " size="+atlas.alpha().width()+"x"+atlas.alpha().height()+" minFilter="+atlas.minFilter()+
                " magFilter="+atlas.magFilter()+" wrapU="+atlas.wrapU()+" wrapV="+atlas.wrapV()+" baseLevelOnly=true");
        var geometry = new LoadedReceiverWorld(epoch.world());
        var seen = new HashSet<String>();
        var packets = new java.util.ArrayList<ReceiverPlantPacket>();
        var materialPackets = new java.util.ArrayList<ReceiverPlantMaterialPacket>();
        var owners = new java.util.ArrayList<ReceiverSodiumScope.GeometrySnapshot>();
        var regionStates = new java.util.ArrayList<ReceiverModelStateWitness.Owner>();
        var expectedPlantOwners = new java.util.ArrayList<ReceiverModelStateWitness.Owner>();
        int unavailable = 0;
        int unloadedCells = 0, retainedTriangles = 0;
        if(requestedWindow!=null) {
            var halo=new ReceiverPlantCellIndex.Window(requestedWindow.x(),requestedWindow.y(),requestedWindow.z(),
                    requestedWindow.width(),requestedWindow.height(),requestedWindow.depth()).expanded(1,geometry.minY(),geometry.maxY());
            requestedWindow=new ReceiverRunPublisher.Window(halo.x(),halo.y(),halo.z(),halo.width(),halo.height(),halo.depth());
        }
        int bottom = requestedWindow==null?Math.max(geometry.minY(),top-12):requestedWindow.y();
        int ceiling = requestedWindow==null?Math.min(geometry.maxY(),top+3):requestedWindow.y()+requestedWindow.height();
        int scanMinX=requestedWindow==null?centerX-8:requestedWindow.x();
        int scanMinZ=requestedWindow==null?centerZ-8:requestedWindow.z();
        int width=requestedWindow==null?17:requestedWindow.width();
        int depth=requestedWindow==null?17:requestedWindow.depth();
        var indexWindow=new ReceiverPlantCellIndex.Window(scanMinX-1,bottom-1,scanMinZ-1,width+2,ceiling-bottom+2,depth+2);
        if(bottom<geometry.minY() || ceiling>geometry.maxY())
            throw new IllegalArgumentException("Plant capture window exceeds world height");
        try (var session = new OwnedSodiumReceiver.Session(epoch)) {
            for (int y = bottom; y < ceiling; y++)
                for (int z = scanMinZ; z < scanMinZ+depth; z++)
                    for (int x = scanMinX; x < scanMinX+width; x++) {
                        if (!geometry.loaded(x,z)) { unloadedCells++;continue; }
                        regionStates.add(new ReceiverModelStateWitness.Owner(x,y,z,geometry.blockState(x,y,z)));
                        var cell = geometry.receiverCell(x,y,z);
                        if (!plants.contains(cell.blockId())) continue;
                        expectedPlantOwners.add(regionStates.getLast());
                        try {
                            var model = session.captureGeometry(x,y,z);
                            if (model == null) { unavailable++;continue; }
                            var volumes = java.util.List.of(geometry.waterVolume(x,y,z),geometry.waterVolume(x,y+1,z),geometry.waterVolume(x,y+2,z));
                            boolean stateMatch = volumes.get(0).state().equals(model.state());
                            System.out.println("[Aqualumen Receiver] plant-water-volume frame="+epoch.frame()+" resources="+epoch.resources()+
                                    " block="+cell.blockId()+" cell="+x+","+y+","+z+" heights="+volumes.get(0).height()+","+
                                    volumes.get(1).height()+","+volumes.get(2).height()+" fullColumn="+ReceiverWaterVolume.fullColumn(volumes)+
                                    " modelStateMatch="+stateMatch+" traceAdmission=false");
                            if (!stateMatch) throw new IllegalStateException("Plant fluid/model state differs");
                            var decoded = terrain.decodeGeometry(model,(textureU,textureV) -> ReceiverQuadIntersection.Coverage.UNKNOWN);
                            if (decoded == null) throw new IllegalStateException("Owned model UV decoding unavailable");
                            var modelPacket = ReceiverPlantPacket.capture(epoch,decoded,centerX,top,centerZ,true);
                            var modelBounds=modelPacket.bounds(epoch);
                            System.out.println("[Aqualumen Receiver] plant-world-bounds frame="+epoch.frame()+" resources="+epoch.resources()+
                                    " block="+cell.blockId()+" cell="+x+","+y+","+z+
                                    " min="+modelBounds.minX()+","+modelBounds.minY()+","+modelBounds.minZ()+
                                    " max="+modelBounds.maxX()+","+modelBounds.maxY()+","+modelBounds.maxZ()+" traceAdmission=false");
                            var materials=terrain.decodeMaterialGeometry(model);
                            if(materials==null || materials.size()!=modelPacket.count())
                                throw new IllegalStateException("Owned plant material/geometry triangle order unavailable");
                            var materialPacket=ReceiverPlantMaterialPacket.capture(modelPacket,materials,epoch);
                            if(!materialPacket.owns(modelPacket) || materialPacket.attributes(epoch).length!=modelPacket.count()*24)
                                throw new IllegalStateException("Plant material packet association unavailable");
                            float[] primitives=modelPacket.triangles();
                            for(int primitive=0;primitive<materials.size();primitive++)
                                for(int corner=0;corner<3;corner++) {
                                    var point=materials.get(primitive).sample(corner==0?1:0,corner==1?1:0,corner==2?1:0,false);
                                    int offset=primitive*16+corner*4;
                                    if((float)(point.x()-centerX)!=primitives[offset]
                                            || (float)(point.y()-top)!=primitives[offset+1]
                                            || (float)(point.z()-centerZ)!=primitives[offset+2]
                                            || point.attributes().u()!=primitives[offset+3]
                                            || point.attributes().v()!=primitives[primitive*16+12+corner])
                                        throw new IllegalStateException("Owned plant material vertices differ from intersection packet");
                                }
                            if (modelPacket.count()>ReceiverPlantPacket.MAXIMUM_TRIANGLES-retainedTriangles)
                                throw new IllegalStateException("Plant region triangle capacity exceeded");
                            packets.add(modelPacket);
                            materialPackets.add(materialPacket);
                            retainedTriangles += modelPacket.count();
                            owners.add(model);
                            if (seen.contains(cell.blockId())) continue;
                            materialGpu(model,materials,terrain,lighting,epoch,atlas,wrapU,wrapV);
                            gpu(model,decoded,terrain,epoch);
                            int transparent = 0, opaque = 0;
                            for (var quad : decoded) {
                                for (var triangle : java.util.List.of(
                                        java.util.List.of(quad.first(),quad.second(),quad.third()),
                                        java.util.List.of(quad.first(),quad.third(),quad.fourth()))) {
                                    for (int second = 0; second <= 16; second++)
                                        for (int third = 0; third <= 16-second; third++) {
                                            double weightSecond = second/16.0, weightThird = third/16.0;
                                            double weightFirst = 1-weightSecond-weightThird;
                                            double textureU = triangle.get(0).u()*weightFirst+triangle.get(1).u()*weightSecond+triangle.get(2).u()*weightThird;
                                            double textureV = triangle.get(0).v()*weightFirst+triangle.get(1).v()*weightSecond+triangle.get(2).v()*weightThird;
                                            double alpha = atlas.alpha().sampleBaseLevel(textureU,textureV,filter,wrapU,wrapV);
                                            if (!Double.isFinite(alpha)) throw new IllegalStateException("Unavailable atlas alpha");
                                            if (alpha < 0.1) transparent++; else opaque++;
                                        }
                                }
                            }
                            var now = ReceiverRadianceBridge.epoch();
                            if (!epoch.equals(now)) throw new IllegalStateException("Plant probe epoch changed");
                            seen.add(cell.blockId());
                            int nonUp = 0;
                            float minX = Float.POSITIVE_INFINITY, maxX = Float.NEGATIVE_INFINITY;
                            for (var face : model.faces()) {
                                if (!face.face().equals("UP")) nonUp++;
                                for (var vertex : face.raw()) {
                                    minX = Math.min(minX,vertex.x()-face.offsetX());
                                    maxX = Math.max(maxX,vertex.x()-face.offsetX());
                                }
                            }
                            System.out.println("[Aqualumen Receiver] plant-model-captured frame="+epoch.frame()+
                                    " resources="+epoch.resources()+" block="+cell.blockId()+" cell="+x+","+y+","+z+
                                    " quads="+model.faces().size()+" nonUp="+nonUp+" localX="+minX+","+maxX+
                                    " rawUV=true packedUV=true decodedQuads="+decoded.size()+" transparentSamples="+transparent+
                                    " opaqueSamples="+opaque+" alphaProbeReady=true baseLevelOnly=true alphaReady=false radianceReady=false");
                        } catch (ReflectiveOperationException | RuntimeException error) {
                            unavailable++;
                            seen.add(cell.blockId());
                            System.out.println("[Aqualumen Receiver] plant-model-unavailable block="+cell.blockId()+
                                    " reason="+error.getClass().getSimpleName());
                        }
                    }
        }
        geometry.validateChunks();
        if(unloadedCells!=0)throw new IllegalStateException("Plant owner region includes unloaded cells");
        ReceiverModelStateWitness.verify(regionStates,
                owner->geometry.blockState(owner.x(),owner.y(),owner.z()),()-> {
                    if (!epoch.equals(ReceiverRadianceBridge.epoch()))
                        throw new IllegalStateException("Plant region validation epoch expired");
                });
        ReceiverModelStateWitness.verifyComplete(expectedPlantOwners,owners.stream().map(owner->new ReceiverModelStateWitness.Owner(
                owner.x(),owner.y(),owner.z(),owner.state())).toList(),
                owner->geometry.blockState(owner.x(),owner.y(),owner.z()),()-> {
                    if (!packets.isEmpty() && !packets.getFirst().current(ReceiverRadianceBridge.epoch()))
                        throw new IllegalStateException("Plant owner validation epoch expired");
                });
        if (!packets.isEmpty()) {
            var region = ReceiverPlantPacket.aggregate(epoch,packets,ReceiverPlantPacket.MAXIMUM_TRIANGLES);
            var regionMaterial=ReceiverPlantMaterialPacket.aggregate(region,materialPackets,epoch);
            if(!regionMaterial.owns(region) || regionMaterial.attributes(epoch).length!=region.count()*24)
                throw new IllegalStateException("Plant region material association unavailable");
            materialRegionGpu(regionMaterial,epoch);
            var regionIndex = ReceiverPlantCellIndex.capture(region,indexWindow,epoch,1048576);
            var regionCells=ReceiverPlantCellPublication.capture(regionIndex,epoch,new ReceiverPlantCellPublication.World() {
                public ReceiverRadianceVolume.Epoch epoch() { return ReceiverRadianceBridge.epoch(); }
                public ReceiverPlantCellPublication.Proof proof(int x,int y,int z) {
                    return new ReceiverPlantCellPublication.Proof(java.util.List.of(
                            geometry.waterVolume(x,y,z),geometry.waterVolume(x,y+1,z),geometry.waterVolume(x,y+2,z)),false);
                }
                public void beginValidation() { geometry.validateChunks(); }
            });
            cellRegionGpu(region,regionMaterial,regionCells,epoch);
            if (!region.current(ReceiverRadianceBridge.epoch())) throw new IllegalStateException("Plant region epoch expired");
            geometry.validateChunks();
            ReceiverModelStateWitness.verify(regionStates,
                    owner->geometry.blockState(owner.x(),owner.y(),owner.z()),()-> {
                        if (!region.current(ReceiverRadianceBridge.epoch()))
                            throw new IllegalStateException("Plant final region validation epoch expired");
                    });
            System.out.println("[Aqualumen Receiver] plant-region-aggregated frame="+epoch.frame()+" resources="+epoch.resources()+
                    " models="+owners.size()+" triangles="+region.count()+" memberships="+regionIndex.memberships()+
                    " unavailable="+unavailable+" unloadedCells="+unloadedCells+
                    " regionStatesValidated="+regionStates.size()+
                    " sharedReference=true ownerStatesValidated=true scannedPlantOwnersComplete=true completeModelOwners=false traceAdmission=false");
        }
        System.out.println("[Aqualumen Receiver] plant-model-probe-finished kinds="+seen.size()+" fieldUnchanged=true chunkPointersValidated=true");
    }
    private static ReceiverAtlasAlpha.Wrap wrap(int value) {
        return switch (value) {
            case org.lwjgl.opengl.GL11.GL_REPEAT -> ReceiverAtlasAlpha.Wrap.REPEAT;
            case org.lwjgl.opengl.GL12.GL_CLAMP_TO_EDGE -> ReceiverAtlasAlpha.Wrap.CLAMP;
            default -> throw new IllegalStateException("Unsupported atlas wrap");
        };
    }
    private static void materialRegionGpu(ReceiverPlantMaterialPacket material,ReceiverRadianceVolume.Epoch epoch) {
        Runnable guard=()-> {
            var current=ReceiverRadianceBridge.epoch();
            if(current==null || !current.matches(epoch.world(),epoch.frame(),epoch.resources()))
                throw new IllegalStateException("Plant material region GPU owner expired");
        };
        guard.run();float[] expected=material.attributes(epoch);
        var upload=ReceiverRadianceTextureUpload.plants();
        var payload=ReceiverPlantPacket.texturePayload(6,expected);
        float[] expectedTexture=payload.values();
        int texture=upload.create(payload.width(),payload.height(),expectedTexture);
        int previous=org.lwjgl.opengl.GL11.glGetInteger(org.lwjgl.opengl.GL11.GL_TEXTURE_BINDING_2D);
        try {
            org.lwjgl.opengl.GL11.glBindTexture(org.lwjgl.opengl.GL11.GL_TEXTURE_2D,texture);
            float[] actual=new float[expectedTexture.length];
            org.lwjgl.opengl.GL11.glGetTexImage(org.lwjgl.opengl.GL11.GL_TEXTURE_2D,0,
                    org.lwjgl.opengl.GL11.GL_RGBA,org.lwjgl.opengl.GL11.GL_FLOAT,actual);
            guard.run();
            if(org.lwjgl.opengl.GL11.glGetError()!=org.lwjgl.opengl.GL11.GL_NO_ERROR
                    || !java.util.Arrays.equals(expectedTexture,actual))
                throw new IllegalStateException("Owned plant region material GPU readback differs");
        } finally {
            org.lwjgl.opengl.GL11.glBindTexture(org.lwjgl.opengl.GL11.GL_TEXTURE_2D,previous);upload.delete(texture);
        }
        System.out.println("[Aqualumen Receiver] plant-region-material-gpu frame="+epoch.frame()+" resources="+epoch.resources()
                +" triangles="+material.count()+" attributes="+expected.length+
                " textureExtent="+payload.width()+"x"+payload.height()+" exactReadback=true traceAdmission=false");
    }
    private static void cellRegionGpu(ReceiverPlantPacket geometry,ReceiverPlantMaterialPacket material,
            ReceiverPlantCellPublication cells,ReceiverRadianceVolume.Epoch epoch) {
        var upload=ReceiverRadianceTextureUpload.plants();
        float[] headers=cells.headers(epoch),indices=cells.indices(epoch);
        var primitives=ReceiverPlantPacket.texturePayload(4,geometry.triangles());
        var attributes=ReceiverPlantPacket.texturePayload(6,material.attributes(epoch));
        try(var publisher=new ReceiverPlantPublisher(upload,ReceiverRadianceBridge::epoch)) {
            publisher.publish(geometry,cells,material);
            if(!publisher.ready() || publisher.packet()!=geometry || publisher.material()!=material
                    || publisher.publication()!=cells)
                throw new IllegalStateException("Plant live atomic publication identity differs");
            float[][] expected={headers,indices,primitives.values(),attributes.values()};
            int previous=org.lwjgl.opengl.GL11.glGetInteger(org.lwjgl.opengl.GL11.GL_TEXTURE_BINDING_2D);
            try {
                for(int index=0;index<expected.length;index++) {
                    int texture=index==3?publisher.materialTexture():publisher.texture(index);
                    org.lwjgl.opengl.GL11.glBindTexture(org.lwjgl.opengl.GL11.GL_TEXTURE_2D,texture);
                    float[] actual=new float[expected[index].length];
                    org.lwjgl.opengl.GL11.glGetTexImage(org.lwjgl.opengl.GL11.GL_TEXTURE_2D,0,
                            org.lwjgl.opengl.GL11.GL_RGBA,org.lwjgl.opengl.GL11.GL_FLOAT,actual);
                    if(!java.util.Arrays.equals(expected[index],actual))
                        throw new IllegalStateException("Plant live atomic texture readback differs");
                }
                if(!geometry.current(ReceiverRadianceBridge.epoch())
                        || org.lwjgl.opengl.GL11.glGetError()!=org.lwjgl.opengl.GL11.GL_NO_ERROR)
                    throw new IllegalStateException("Plant live atomic readback owner expired");
            } finally { org.lwjgl.opengl.GL11.glBindTexture(org.lwjgl.opengl.GL11.GL_TEXTURE_2D,previous); }
        }
        int waterCells=0,completeCells=0;
        var window=cells.window();
        for(int cell=0;cell<window.width()*window.height()*window.depth();cell++) {
            if(headers[cell*4+2]==1)waterCells++;
            if(headers[cell*4+3]==1)completeCells++;
        }
        System.out.println("[Aqualumen Receiver] plant-region-cell-gpu frame="+epoch.frame()+" resources="+epoch.resources()+
                " triangles="+geometry.count()+" memberships="+cells.memberships()+" fullWaterCells="+waterCells+
                " completeOwnerCells="+completeCells+" exactReadback=true traceAdmission=false");
    }
    private static void materialGpu(ReceiverSodiumScope.GeometrySnapshot model,
            java.util.List<ReceiverMaterialTriangle> triangles,ReceiverTerrainState terrain,
            ReceiverLightingState lighting,ReceiverRadianceVolume.Epoch epoch,ReceiverAtlasReadback.Image atlas,
            ReceiverAtlasAlpha.Wrap wrapU,ReceiverAtlasAlpha.Wrap wrapV) {
        var filter=switch(atlas.magFilter()) {
            case org.lwjgl.opengl.GL11.GL_NEAREST -> ReceiverAtlasAlpha.Filter.NEAREST;
            case org.lwjgl.opengl.GL11.GL_LINEAR -> ReceiverAtlasAlpha.Filter.LINEAR;
            default -> throw new IllegalStateException("Unqualified material point atlas magnification filter");
        };
        var points=new java.util.ArrayList<ReceiverMaterialPoint>();
        for(var triangle:triangles)
            for(int second=0;second<=4;second++)for(int third=0;third<=4-second;third++)
                points.add(triangle.sample(1-second/4.0-third/4.0,second/4.0,third/4.0,false));
        int opaque=0,transparent=0,positive=0;double total=0,sun=0;
        try(var session=new ReceiverSourceDraw.Session(epoch)) {
            var results=ReceiverSourceDraw.cutoutMaterialPoints(session,points,terrain,lighting,epoch);
            for(int index=0;index<points.size();index++) {
                var point=points.get(index);var result=results.get(index);
                double alpha=atlas.alpha().sampleBaseLevel(point.attributes().u(),point.attributes().v(),filter,wrapU,wrapV);
                if(!Double.isFinite(alpha))throw new IllegalStateException("Plant material point alpha unavailable");
                boolean admitted=alpha>=.1;
                if(result.total().get(3)!=(admitted?1f:0f))
                    throw new IllegalStateException("Plant material source readiness differs from owned atlas alpha");
                if(admitted)opaque++;else transparent++;
                double rgb=0;
                for(int channel=0;channel<3;channel++) {
                    rgb+=result.total().get(channel);total+=result.total().get(channel);sun+=result.sun().get(channel);
                }
                if(admitted && rgb>0)positive++;
            }
        }
        if(opaque<1 || positive<1)throw new IllegalStateException("Vacuous plant material source draw");
        if(!epoch.equals(ReceiverRadianceBridge.epoch()))throw new IllegalStateException("Plant material draw epoch expired");
        System.out.println("[Aqualumen Receiver] plant-material-gpu frame="+epoch.frame()+" resources="+epoch.resources()
                +" state="+model.state()+" triangles="+triangles.size()+" samples="+points.size()+" opaque="+opaque
                +" transparent="+transparent+" positive="+positive+" totalRgbSum="+total+" sunRgbSum="+sun
                +" originalSourceFragment=true geometricNormals=true pointGradientsZero=true traceAdmission=false");
    }

    private static void gpu(ReceiverSodiumScope.GeometrySnapshot model,
            java.util.List<ReceiverQuadIntersection.Quad> quads, ReceiverTerrainState terrain,
            ReceiverRadianceVolume.Epoch epoch) {
        var packet = ReceiverPlantPacket.capture(epoch,quads,model.x(),model.y(),model.z(),true);
        var rays = new java.util.ArrayList<ReceiverQuadIntersection.Ray>();
        for (var quad : quads) {
            for (var triangle : java.util.List.of(java.util.List.of(quad.first(),quad.second(),quad.third()),
                    java.util.List.of(quad.first(),quad.third(),quad.fourth()))) {
                var first = triangle.get(0); var second = triangle.get(1); var third = triangle.get(2);
                double edgeX=second.x()-first.x(),edgeY=second.y()-first.y(),edgeZ=second.z()-first.z();
                double otherX=third.x()-first.x(),otherY=third.y()-first.y(),otherZ=third.z()-first.z();
                double normalX=edgeY*otherZ-edgeZ*otherY,normalY=edgeZ*otherX-edgeX*otherZ,normalZ=edgeX*otherY-edgeY*otherX;
                double length=Math.sqrt(normalX*normalX+normalY*normalY+normalZ*normalZ);
                if (!Double.isFinite(length) || length<1e-8) throw new IllegalStateException("Degenerate actual plant model");
                normalX/=length; normalY/=length; normalZ/=length;
                for (int weightSecond=0;weightSecond<=4;weightSecond++)
                    for (int weightThird=0;weightThird<=4-weightSecond;weightThird++) {
                        double middle=weightSecond/4.0,last=weightThird/4.0,start=1-middle-last;
                        rays.add(new ReceiverQuadIntersection.Ray(first.x()*start+second.x()*middle+third.x()*last+normalX*.2,
                                first.y()*start+second.y()*middle+third.y()*last+normalY*.2,
                                first.z()*start+second.z()*middle+third.z()*last+normalZ*.2,-normalX,-normalY,-normalZ,1));
                    }
            }
        }
        String kernel;
        try (var input=ReceiverPlantGpuProbe.class.getResourceAsStream("water_plant_intersection.glsl")) {
            if (input==null) throw new IllegalStateException("Owned plant GPU kernel missing");
            byte[] bytes=input.readAllBytes();
            if (bytes.length<1 || bytes.length>32768) throw new IllegalStateException("Unbounded plant GPU kernel");
            kernel=new String(bytes,java.nio.charset.StandardCharsets.UTF_8);
        } catch (java.io.IOException error) { throw new IllegalStateException("Plant GPU kernel unreadable",error); }
        Runnable guard=() -> {
            var now=ReceiverRadianceBridge.epoch();
            if (!packet.current(now)) throw new IllegalStateException("Plant GPU probe epoch expired");
        };
        float[] result=ReceiverPlantGpuProbe.draw(packet,rays,terrain.atlas(),terrain.sampler(),epoch,guard,kernel);
        int clear=0,visible=0,unknown=0;
        for (int offset=0;offset<result.length;offset+=4) {
            if (result[offset]==0) clear++; else if (result[offset]==1) visible++; else if (result[offset]==2) unknown++;
            else throw new IllegalStateException("Malformed actual plant GPU result");
        }
        System.out.println("[Aqualumen Receiver] plant-gpu-probed frame="+epoch.frame()+" resources="+epoch.resources()+
                " cell="+model.x()+","+model.y()+","+model.z()+" triangles="+packet.count()+" rays="+rays.size()+
                " clear="+clear+" visible="+visible+" unknown="+unknown+" lod=0 footprint=point standalone=true radianceReady=false");
    }
}
