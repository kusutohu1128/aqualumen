package dev.aqualumen.physics;

import net.irisshaders.iris.Iris;
import net.irisshaders.iris.gl.sampler.SamplerHolder;
import net.irisshaders.iris.gl.uniform.UniformHolder;
import net.irisshaders.iris.gl.uniform.UniformUpdateFrequency;
import net.irisshaders.iris.uniforms.CameraUniforms;
import net.irisshaders.iris.uniforms.SystemTimeUniforms;
import org.joml.Vector3f;
import org.joml.Vector3i;
import org.joml.Vector2i;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL20;
import org.lwjgl.opengl.GL30;
import java.util.HashSet;
import java.util.Set;
import java.util.Arrays;

public final class ReceiverRadianceBridge {
    private static final ReceiverRadiancePublisher publisher = new ReceiverRadiancePublisher(new ReceiverRadianceTextureUpload());
    private static final ReceiverRunPublisher runPublisher = new ReceiverRunPublisher(new ReceiverRadianceTextureUpload());
    private static long generation;
    private static final ReceiverPackEligibility packEligibility=new ReceiverPackEligibility();
    private static ReceiverLightingState lighting;
    private static ReceiverRadianceVolume.Epoch attemptedEpoch;
    private static final Set<Integer> attemptedPrograms = new HashSet<>();
    private static final Set<Integer> reportedPrograms = new HashSet<>();
    private static boolean reportedLighting;
    private static boolean reportedSource;
    private static boolean reportedSodium;
    private static final ReceiverSourceSchedule sourceSchedule=new ReceiverSourceSchedule();
    private static int sodiumFailures;
    private static boolean reportedPublication;
    private static long publicationTraceFrame=-1;
    private static ReceiverDrawBinding drawBinding;

    private ReceiverRadianceBridge() { }

    public static ReceiverRadianceVolume.Epoch epoch() {
        Contacts.ensureUpdate();
        Object world = Contacts.currentWorld();
        if (world == null || Contacts.currentDimension() != 0 || !Iris.isPackInUseQuick() ||
                !packEligibility.accepts(Iris.getCurrentPackName())) return null;
        return new ReceiverRadianceVolume.Epoch(world, SystemTimeUniforms.COUNTER.getAsInt(), generation);
    }

    static boolean lightingCurrent(ReceiverLightingState snapshot) {
        Contacts.ensureUpdate();
        Object world=Contacts.currentWorld();
        return snapshot!=null && world!=null && Contacts.currentDimension()==0
                && Iris.isPackInUseQuick() && packEligibility.accepts(Iris.getCurrentPackName())
                && snapshot.current(world,SystemTimeUniforms.COUNTER.getAsInt(),generation);
    }

    public static void publish(ReceiverRadianceVolume volume) {
        runPublisher.invalidate();
        publisher.publish(volume, epoch());
    }

    public static void invalidate() {
        generation++; publisher.invalidate(); runPublisher.invalidate(); lighting = null; attemptedEpoch = null;
        attemptedPrograms.clear(); reportedPrograms.clear(); reportedLighting = false; reportedSource = false;
        reportedSodium = false; sourceSchedule.reset(); sodiumFailures = 0;
        reportedPublication = false;
        publicationTraceFrame=-1;
    }

    public static void sourceReady() {
        int program = GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if (program == 0 || GL20.glGetUniformLocation(program, "receiverInputSize") < 0) return;
        shaderReady();
        if (!reportedSource) {
            reportedSource = true;
            int framebuffer = GL11.glGetInteger(GL30.GL_DRAW_FRAMEBUFFER_BINDING);
            int[] size = new int[2];
            GL20.glGetUniformiv(program, GL20.glGetUniformLocation(program, "receiverInputSize"), size);
            System.out.println("[Aqualumen Receiver] source-pass-bound frame=" + SystemTimeUniforms.COUNTER.getAsInt() +
                    " program=" + program + " inputSize=" + size[0] + "x" + size[1] + " framebuffer=" + framebuffer +
                    " total=" + sourceAttachment(framebuffer, GL30.GL_COLOR_ATTACHMENT0) +
                    " direct=" + sourceAttachment(framebuffer, GL30.GL_COLOR_ATTACHMENT1));
        }
    }

    public static void terrainReady() {
        var now=epoch();
        try { drawBinding=runPublisher.ready(now)==2?ReceiverDrawBinding.open(runPublisher,now):ReceiverDrawBinding.open(publisher,now); }
        catch(IllegalStateException unavailable) {
            if(sodiumFailures++<8) System.out.println("[Aqualumen Receiver] draw-binding-unavailable "+unavailable);
        }
        observePublication(now);
        if(sourceSchedule.attempted(now) || now==null || lighting==null || !lighting.current(now)) return;
        try {
            var terrain=ReceiverTerrainState.capture(now);
            if(terrain!=null) captureSodium(terrain);
        } catch(IllegalStateException error) {
            if(sodiumFailures++<8) System.out.println("[Aqualumen Receiver] terrain-input-unavailable "+error);
        }
    }

    public static void terrainFinished() {
        var binding=drawBinding; drawBinding=null;
        if(binding!=null) binding.close();
    }

    private static void captureSodium(ReceiverTerrainState terrain) {
        var now = epoch();
        if (lighting == null || !lighting.current(now) || !sourceSchedule.reserve(now)) return;
        long start=System.nanoTime();
        try {
            float[] camera = lighting.value("cameraPosition");
            int centerX = (int)Math.floor(camera[0]), centerZ = (int)Math.floor(camera[2]), top = (int)Math.floor(camera[1]);
            if (Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantRegion-v69-2026-10-11.zip")
                    || Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantMaterial-v85-2026-10-11.zip")
                    || Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantMaterial-v86-2026-10-11.zip")
                    || Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantOwnerBounds-v96-2026-10-11.zip"))
                ReceiverPlantProbe.capture(now,centerX,top,centerZ,terrain,lighting);
            var geometry = new LoadedReceiverWorld(now.world());
            int minY=Math.max(geometry.minY(),top-30), maxY=Math.min(geometry.maxY(),top+6);
            if(maxY<=minY) return;
            var bounds=new ReceiverRunPublisher.Window(centerX-43,minY,centerZ-43,87,maxY-minY,87);
            if(Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantReceiverWindow-v97-2026-10-11.zip")
                    || Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantTiledWindow-v98-2026-10-11.zip")
                    || Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantFluidPublication-v99-2026-10-11.zip")
                    || Iris.getCurrentPackName().equals("Aqualumen-DisplayWater-PlantOwnerHalo-v100-2026-10-11.zip"))
                ReceiverPlantProbe.capture(now,centerX,top,centerZ,terrain,lighting,bounds);
            ReceiverRunSourceCapture.Result captured;
            int meshCaptures,sectionCopies,sourceBatches,geometryReads;
            long meshingNanos,drawNanos;
            String annotationPack=Iris.getCurrentPackName();
            boolean annotateUnknown=annotationPack.equals("Aqualumen-DisplayWater-ReceiverUnknownKinds-v52-2026-10-11.zip")
                    || annotationPack.equals("Aqualumen-RawUnknownKindsDiagnostic-v95-2026-10-11.zip");
            try(var sourceWorld=new LoadedReceiverSourceWorld(now,terrain,lighting,bounds)) {
                captured=ReceiverRunSourceCapture.capture(sourceWorld,bounds,now,annotateUnknown);
                meshCaptures=sourceWorld.meshCaptures(); sectionCopies=sourceWorld.sectionCopies(); sourceBatches=sourceWorld.sourceBatches();
                geometryReads=sourceWorld.geometryReads();
                meshingNanos=sourceWorld.meshingNanos();drawNanos=sourceWorld.drawNanos();
            }
            publisher.invalidate();
            runPublisher.publish(bounds,captured.layout(),captured.radiance(),epoch());
            var volume=captured.radiance();
            if(!reportedSodium || now.frame()%60==0) {
                reportedSodium=true;
                int sources=0,partials=0,airCaps=0; float[] values=volume.source(), cells=volume.cells();
                for(int offset=3;offset<values.length;offset+=4) if(values[offset]==1) sources++;
                for(int offset=0;offset<cells.length;offset+=4) if(cells[offset]==4) partials++;
                for(int offset=0;offset<cells.length;offset+=4) if(cells[offset]==5) airCaps++;
                System.out.println("[Aqualumen Receiver] source-runs-updated frame="+now.frame()+" resources="+now.resources()+
                        " bounds="+bounds+" records="+volume.records()+" sources="+sources+" partials="+partials+" airCaps="+airCaps+" meshCaptures="+meshCaptures+
                        " sectionCopies="+sectionCopies+" sourceBatches="+sourceBatches+" geometryReads="+geometryReads+" ready="+runPublisher.ready(now)+" unknownKinds="+annotateUnknown+
                        " producerMs="+(System.nanoTime()-start)/1e6+
                        " collectionMs="+captured.timings().collection()/1e6+" shadingMs="+captured.timings().shading()/1e6+
                        " validationMs="+captured.timings().validation()/1e6+" packingMs="+captured.timings().packing()/1e6+
                        " meshingMs="+meshingNanos/1e6+" sourceDrawWallMs="+drawNanos/1e6+" approximation=face-center-point");
            }
        } catch (ReflectiveOperationException | RuntimeException error) {
            Throwable cause = error;
            for (int depth = 0; depth < 8 && cause.getCause() != null; depth++) cause = cause.getCause();
            if (sodiumFailures++ < 8) System.out.println("[Aqualumen Receiver] owned-sodium-unavailable " + cause);
        }
    }

    private static void observePublication(ReceiverRadianceVolume.Epoch now) {
        if(now==null || ready(now)!=2 || publicationTraceFrame==now.frame()
                || reportedPublication && now.frame()%60!=0) return;
        int program=GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        int location=GL20.glGetUniformLocation(program,"aqualumenReceiverReady");
        if(location<0) return;
        int ready=GL20.glGetUniformi(program,location);
        if(ready!=2) return;
        var bindings=new StringBuilder(); int active=GL11.glGetInteger(org.lwjgl.opengl.GL13.GL_ACTIVE_TEXTURE);
        boolean runs=runPublisher.ready(now)==2;
        int runMode=0,runCount=0;
        if(runs) {
            int modeLocation=GL20.glGetUniformLocation(program,"aqualumenReceiverRunMode");
            int countLocation=GL20.glGetUniformLocation(program,"aqualumenReceiverRunCount");
            if(modeLocation<0 || countLocation<0)return;
            runMode=GL20.glGetUniformi(program,modeLocation);runCount=GL20.glGetUniformi(program,countLocation);
            if(runMode!=1 || runCount!=runPublisher.records(now))return;
        }
        String[] names=runs?new String[]{"aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces","aqualumenReceiverRunHeaders","aqualumenReceiverRunRanges"}
            :new String[]{"aqualumenReceiverCells","aqualumenReceiverSource","aqualumenReceiverSun","aqualumenReceiverFaces"};
        try {
            for(int index=0;index<names.length;index++) {
                int sampler=GL20.glGetUniformLocation(program,names[index]);
                if(sampler<0) return;
                int unit=GL20.glGetUniformi(program,sampler);
                org.lwjgl.opengl.GL13.glActiveTexture(org.lwjgl.opengl.GL13.GL_TEXTURE0+unit);
                int texture=GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
                if(texture!=texture(index,now)) return;
                bindings.append(names[index]).append('=').append(texture).append('@').append(unit).append(' ');
            }
            reportedPublication=true;
            publicationTraceFrame=now.frame();
            System.out.println("[Aqualumen Receiver] published-field-bound frame="+now.frame()+" program="+program+" ready="+ready+" runMode="+runMode+" runCount="+runCount+" "+bindings);
        } finally { org.lwjgl.opengl.GL13.glActiveTexture(active); }
    }

    private static String sourceAttachment(int framebuffer, int attachment) {
        if (framebuffer == 0 || GL30.glGetFramebufferAttachmentParameteri(GL30.GL_DRAW_FRAMEBUFFER, attachment,
                GL30.GL_FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE) != GL11.GL_TEXTURE) return "unavailable";
        int texture = GL30.glGetFramebufferAttachmentParameteri(GL30.GL_DRAW_FRAMEBUFFER, attachment,
                GL30.GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME);
        int binding = GL11.glGetInteger(GL11.GL_TEXTURE_BINDING_2D);
        try {
            GL11.glBindTexture(GL11.GL_TEXTURE_2D, texture);
            return texture + ":" + GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_WIDTH) + "x" +
                    GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_HEIGHT) + ":format=" +
                    GL11.glGetTexLevelParameteri(GL11.GL_TEXTURE_2D,0,GL11.GL_TEXTURE_INTERNAL_FORMAT);
        } finally { GL11.glBindTexture(GL11.GL_TEXTURE_2D, binding); }
    }

    public static void shaderReady() {
        var now = epoch();
        if (now == null || lighting != null && lighting.current(now)) return;
        if (attemptedEpoch == null || attemptedEpoch.world() != now.world() || attemptedEpoch.frame() != now.frame() ||
                attemptedEpoch.resources() != now.resources()) {
            attemptedEpoch = now; attemptedPrograms.clear();
        }
        int program = GL11.glGetInteger(GL20.GL_CURRENT_PROGRAM);
        if (!attemptedPrograms.add(program)) return;
        try {
            lighting = ReceiverLightingState.capture(now);
            if (!reportedLighting) {
                reportedLighting = true;
                System.out.println("[Aqualumen Receiver] lighting-captured frame=" + now.frame() + " resources=" + now.resources() +
                        " program=" + lighting.program() + " sky=" + lighting.texture("colortex6") +
                        " clear=" + lighting.texture("colortex7") + " shadow=" + lighting.texture("shadowtex0") +
                        " camera=" + Arrays.toString(lighting.value("cameraPosition")) +
                        " sun=" + Arrays.toString(lighting.value("sunPosition")) +
                        " rain=" + lighting.value("rainStrength")[0] + " cloudTime=" + lighting.value("frameTimeCounter")[0]);
            }
        } catch (IllegalStateException unavailable) {
            if (reportedPrograms.size() < 8 && reportedPrograms.add(program))
                System.out.println("[Aqualumen Receiver] lighting-unavailable program=" + program + " reason=" + unavailable.getMessage());
        }
    }

    public static void register(UniformHolder holder) {
        invalidate();
        holder.uniform2i(UniformUpdateFrequency.PER_FRAME, "receiverInputSize", Vector2i::new);
        holder.uniform1i(UniformUpdateFrequency.PER_FRAME, "aqualumenReceiverReady", () -> ready(epoch()));
        holder.uniform1i(UniformUpdateFrequency.PER_FRAME, "aqualumenReceiverRunMode", () -> runPublisher.ready(epoch())==2?1:0);
        holder.uniform1i(UniformUpdateFrequency.PER_FRAME, "aqualumenReceiverRunCount", () -> runPublisher.records(epoch()));
        holder.uniform3i(UniformUpdateFrequency.PER_FRAME, "aqualumenReceiverSize", () -> {
            var bounds = window(epoch());
            return bounds == null ? new Vector3i() : new Vector3i(bounds.width(), bounds.height(), bounds.depth());
        });
        holder.uniform3f(UniformUpdateFrequency.PER_FRAME, "aqualumenReceiverOrigin", () -> {
            var bounds = window(epoch());
            var camera = CameraUniforms.getUnshiftedCameraPosition();
            return bounds == null ? new Vector3f() : new Vector3f((float)(bounds.x()-camera.x), (float)(bounds.y()-camera.y), (float)(bounds.z()-camera.z));
        });
    }

    public static void register(SamplerHolder holder) {
        String[] inputs = {"receiverInputTexel", "receiverInputTint", "receiverInputNormal", "receiverInputPosition", "receiverInputLightmap", "receiverInputUv", "receiverInputGradients", "receiverAtlas"};
        for (String name : inputs) if (holder.hasSampler(name)) holder.addDynamicSampler(() -> 0, name);
        String[] names = {"aqualumenReceiverCells", "aqualumenReceiverSource", "aqualumenReceiverSun", "aqualumenReceiverFaces", "aqualumenReceiverRunHeaders", "aqualumenReceiverRunRanges"};
        for (int index = 0; index < names.length; index++) {
            int slot = index;
            if (holder.hasSampler(names[index])) holder.addDynamicSampler(() -> texture(slot, epoch()), names[index]);
        }
    }
    private static int ready(ReceiverRadianceVolume.Epoch now) { return runPublisher.ready(now)==2?2:publisher.ready(now); }
    private static int texture(int slot,ReceiverRadianceVolume.Epoch now) {
        return runPublisher.ready(now)==2?runPublisher.texture(slot,now):slot<4?publisher.texture(slot,now):0;
    }
    private static ReceiverRunPublisher.Window window(ReceiverRadianceVolume.Epoch now) {
        if(runPublisher.ready(now)==2)return runPublisher.window(now);
        var bounds=publisher.bounds(now);
        return bounds==null?null:new ReceiverRunPublisher.Window(bounds.x(),bounds.y(),bounds.z(),bounds.width(),bounds.height(),bounds.depth());
    }
}
