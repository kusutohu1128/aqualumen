package dev.aqualumen.physics;

import java.lang.reflect.*;
import java.util.List;

/** Optional read-only actual vanilla face adapter; no registration/cache/GL/shaded RGB. */
final class LoadedReceiverFaces {
    record Source(int x, int y, int z, String blockState, long renderingSeed, ReceiverFace.Face face) {}
    record Material(Source source,ReceiverTexture.Snapshot texture) {}
    private static final class Api {
        final Constructor<?> position;
        final Method block, renderer, colors, model, quads, seed, random, directionX, directionY, directionZ;
        final Method data, face, sprite, tinted, tintIndex, shade, atlas, contents, spriteId, minU, maxU, minV, maxV;
        final Method tint, light, brightness;
        final Object[] directions;
        final Object sky, blockLight;
        Api() throws ReflectiveOperationException {
            Class<?> pos=Class.forName("net.minecraft.class_2338"), state=Class.forName("net.minecraft.class_2680");
            Class<?> dir=Class.forName("net.minecraft.class_2350"), rng=Class.forName("net.minecraft.class_5819");
            Class<?> view=Class.forName("net.minecraft.class_1920"), client=Class.forName("net.minecraft.class_310");
            Class<?> q=Class.forName("net.minecraft.class_777"), s=Class.forName("net.minecraft.class_1058");
            Object format=Class.forName("net.minecraft.class_290").getField("field_1590").get(null);
            if((int)Class.forName("net.minecraft.class_293").getMethod("method_1362").invoke(format)!=32)
                throw new IllegalStateException("Pinned BLOCK vertex format must be 32 bytes");
            position=pos.getConstructor(int.class,int.class,int.class);
            block=Class.forName("net.minecraft.class_1922").getMethod("method_8320",pos);
            renderer=client.getMethod("method_1541");colors=client.getMethod("method_1505");
            model=Class.forName("net.minecraft.class_776").getMethod("method_3349",state);
            quads=Class.forName("net.minecraft.class_1087").getMethod("method_4707",state,dir,rng);
            seed=state.getMethod("method_26190",pos);random=rng.getMethod("method_43049",long.class);
            directions=(Object[])dir.getMethod("values").invoke(null);
            directionX=dir.getMethod("method_10148");directionY=dir.getMethod("method_10164");directionZ=dir.getMethod("method_10165");
            data=q.getMethod("method_3357");face=q.getMethod("method_3358");sprite=q.getMethod("method_35788");
            tinted=q.getMethod("method_3360");tintIndex=q.getMethod("method_3359");shade=q.getMethod("method_24874");
            atlas=s.getMethod("method_45852");contents=s.getMethod("method_45851");
            spriteId=Class.forName("net.minecraft.class_7764").getMethod("method_45816");
            minU=s.getMethod("method_4594");maxU=s.getMethod("method_4577");minV=s.getMethod("method_4593");maxV=s.getMethod("method_4575");
            tint=Class.forName("net.minecraft.class_324").getMethod("method_1697",state,view,pos,int.class);
            Class<?> lightType=Class.forName("net.minecraft.class_1944");
            sky=lightType.getField("field_9284").get(null);blockLight=lightType.getField("field_9282").get(null);
            light=view.getMethod("method_8314",lightType,pos);brightness=view.getMethod("method_24852",dir,boolean.class);
        }
    }
    private static Api api;
    private final Object world, client;
    private final LoadedWorld chunks;
    private final LoadedReceiverWorld geometry;
    LoadedReceiverFaces(Object client,Object world) throws ReflectiveOperationException {
        if(api==null)api=new Api();
        this.client=client;this.world=world;chunks=new LoadedWorld(world);geometry=new LoadedReceiverWorld(world);
    }
    /** One face only, preserving its actual UV/tint and raw unsmoothed lighting inputs. */
    Source faceAt(int x,int y,int z,int nx,int ny,int nz) {
        Material result=readAt(x,y,z,nx,ny,nz,false);
        return result==null?null:result.source();
    }
    /** Face and static mip0 data copied from the same actual quad/sprite call. */
    Material materialAt(int x,int y,int z,int nx,int ny,int nz) {
        return readAt(x,y,z,nx,ny,nz,true);
    }
    private Material readAt(int x,int y,int z,int nx,int ny,int nz,boolean texture) {
        try {
            if(geometry.receiverCell(x,y,z).kind()!=ReceiverField.Kind.OPAQUE) return null;
            Object direction=null;
            for(Object d:api.directions) if((int)api.directionX.invoke(d)==nx && (int)api.directionY.invoke(d)==ny
                    && (int)api.directionZ.invoke(d)==nz) direction=d;
            if(direction==null || !chunks.loaded(x+nx,z+nz) || y+ny<chunks.minY() || y+ny>=chunks.maxY()) return null;
            Object pos=api.position.newInstance(x,y,z),neighbor=api.position.newInstance(x+nx,y+ny,z+nz);
            Object state=api.block.invoke(chunks.existing(x,z),pos),model=api.model.invoke(api.renderer.invoke(client),state);
            long seed=(long)api.seed.invoke(state,pos);
            // Unculled/additional geometry is not represented by one opaque face.
            if(!((List<?>)api.quads.invoke(model,state,null,api.random.invoke(null,seed))).isEmpty()) return null;
            List<?> quads=(List<?>)api.quads.invoke(model,state,direction,api.random.invoke(null,seed));
            if(quads.size()!=1) return null;
            Object quad=quads.get(0);if(api.face.invoke(quad)!=direction)return null;
            int tint=0xffffff;
            if((boolean)api.tinted.invoke(quad)) {
                // Vanilla biome blending can access surrounding columns. Require
                // the conservative maximum 7-block radius already loaded first.
                for(int dz=-7;dz<=7;dz++)for(int dx=-7;dx<=7;dx++)if(!chunks.loaded(x+dx,z+dz))return null;
                tint=(int)api.tint.invoke(api.colors.invoke(client),state,world,pos,(int)api.tintIndex.invoke(quad));
            }
            Object sprite=api.sprite.invoke(quad);
            var descriptor=new ReceiverFace.Sprite(api.atlas.invoke(sprite).toString(),api.spriteId.invoke(api.contents.invoke(sprite)).toString(),
                    (float)api.minU.invoke(sprite),(float)api.maxU.invoke(sprite),(float)api.minV.invoke(sprite),(float)api.maxV.invoke(sprite));
            boolean shade=(boolean)api.shade.invoke(quad);
            var decoded=ReceiverFace.decode((int[])api.data.invoke(quad),nx,ny,nz,descriptor,tint,shade,
                    (int)api.light.invoke(world,api.sky,neighbor),(int)api.light.invoke(world,api.blockLight,neighbor),
                    (float)api.brightness.invoke(world,direction,shade));
            return decoded==null?null:new Material(new Source(x,y,z,state.toString(),seed,decoded),
                    texture?LoadedReceiverTexture.capture(sprite,descriptor):null);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("Pinned vanilla receiver face boundary unavailable",e);
        }
    }
}
