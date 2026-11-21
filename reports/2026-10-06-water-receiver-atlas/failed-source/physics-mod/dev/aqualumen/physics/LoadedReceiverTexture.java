package dev.aqualumen.physics;

import java.lang.reflect.*;
import java.nio.ByteOrder;

/** Pinned, render-thread-only, read-only static SpriteContents mip0 copy. No GL. */
final class LoadedReceiverTexture {
    private static final class Api {
        final Method contents,contentWidth,contentHeight,width,height,format,pixel,renderThread;
        final Field baseImage,animation;
        final Object rgba;
        Api() throws ReflectiveOperationException {
            Class<?> sprite=Class.forName("net.minecraft.class_1058"),content=Class.forName("net.minecraft.class_7764");
            Class<?> image=Class.forName("net.minecraft.class_1011");
            contents=sprite.getMethod("method_45851");contentWidth=content.getMethod("method_45807");contentHeight=content.getMethod("method_45815");
            baseImage=content.getDeclaredField("field_40539");baseImage.setAccessible(true);
            animation=content.getDeclaredField("field_40541");animation.setAccessible(true);
            width=image.getMethod("method_4307");height=image.getMethod("method_4323");format=image.getMethod("method_4318");pixel=image.getMethod("method_4315",int.class,int.class);
            rgba=Class.forName("net.minecraft.class_1011$class_1012").getField("field_4997").get(null);
            renderThread=Class.forName("com.mojang.blaze3d.systems.RenderSystem").getMethod("isOnRenderThread");
        }
    }
    private static Api api;
    static ReceiverTexture.Snapshot capture(Object sprite,ReceiverFace.Sprite descriptor) throws ReflectiveOperationException {
        if(api==null)api=new Api();
        if(!(boolean)api.renderThread.invoke(null) || ByteOrder.nativeOrder()!=ByteOrder.LITTLE_ENDIAN)return null;
        Object content=api.contents.invoke(sprite);
        // Inspect metadata only; constructing a SpriteAnimator can allocate or
        // modify interpolation resources and is not a read-only readiness check.
        if(api.animation.get(content)!=null)return null;
        Object image=api.baseImage.get(content);
        int width=(int)api.width.invoke(image),height=(int)api.height.invoke(image);
        if(width<1 || height<1 || width>256 || height>256 || api.format.invoke(image)!=api.rgba
                || width!=(int)api.contentWidth.invoke(content) || height!=(int)api.contentHeight.invoke(content))return null;
        int[] pixels=new int[width*height];
        for(int y=0;y<height;y++)for(int x=0;x<width;x++)pixels[y*width+x]=(int)api.pixel.invoke(image,x,y);
        return ReceiverTexture.capture(descriptor,width,height,pixels,false);
    }
}
