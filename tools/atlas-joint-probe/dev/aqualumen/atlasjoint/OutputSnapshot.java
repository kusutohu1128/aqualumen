package dev.aqualumen.atlasjoint;
import java.util.*;

/** Pure after-quad boundary; no rendering or GL object creation. */
public final class OutputSnapshot {
    public record Pixel(int x,int y) {}
    public record State(int readFbo,int readBuffer,int packBuffer,int alignment,int rowLength,
        int imageHeight,int skipPixels,int skipRows,int skipImages,int swap,int lsb) {}
    public interface Boundary {
        State state()throws Exception;
        int program()throws Exception;
        int frame()throws Exception;
        int[] viewport()throws Exception;
        int drawFbo()throws Exception;
        int outputTexture()throws Exception;
        int colorEncoding()throws Exception;
        boolean srgbEnabled()throws Exception;
        float[] read(int drawFbo,List<Pixel> points)throws Exception;
        default Map<String,Object> readMetadata(){return Map.of();}
        void restore(State saved)throws Exception;
    }
    public static Map<String,Object> capture(int program,int frame,int fbo,int texture,List<Pixel> pixels,Boundary b) {
        Map<String,Object> r=new LinkedHashMap<>();r.put("available",false);r.put("stateRestored",false);
        r.put("errorFlagConsumed",false);r.put("physicalAccepted",false);r.put("visualAccepted",false);
        State saved=null;
        try {
            if(program<=0||frame<0||fbo<=0||texture<=0||pixels==null||pixels.isEmpty()||pixels.size()>128)
                throw new IllegalArgumentException();
            for(Pixel p:pixels)if(p.x()<0||p.x()>=1600||p.y()<0||p.y()>=900)throw new IllegalArgumentException();
            saved=b.state();r.put("stateBefore",values(saved));
            if(b.program()!=program||b.frame()!=frame||b.drawFbo()!=fbo||b.outputTexture()!=texture
                ||!Arrays.equals(b.viewport(),new int[]{0,0,1600,900}))throw new IllegalStateException("draw seam");
            r.put("drawFramebuffer",fbo);r.put("colorTexture",texture);
            int encoding=b.colorEncoding();boolean srgb=b.srgbEnabled();
            r.put("colorEncoding",encoding);r.put("framebufferSrgbEnabled",srgb);
            if(encoding!=9729||srgb)throw new IllegalStateException("unsupported output conversion");
            float[] rgba=b.read(fbo,pixels);
            r.put("readMetadata",b.readMetadata());
            if(rgba==null||rgba.length!=pixels.size()*4)throw new IllegalStateException("incomplete output");
            List<Map<String,Object>> samples=new ArrayList<>();
            for(int i=0;i<pixels.size();i++) {
                List<Double> v=new ArrayList<>();for(int c=0;c<4;c++){float x=rgba[i*4+c];if(!Float.isFinite(x))throw new IllegalStateException();v.add((double)x);}
                samples.add(Map.of("x",pixels.get(i).x(),"y",pixels.get(i).y(),"rgba",v));
            }
            r.put("pixels",samples);
            if(b.program()!=program||b.frame()!=frame||b.drawFbo()!=fbo||b.outputTexture()!=texture
                ||!Arrays.equals(b.viewport(),new int[]{0,0,1600,900}))throw new IllegalStateException("unstable output");
            r.put("available",true);
        }catch(Exception|LinkageError e){r.put("available",false);r.put("errorClass",e.getClass().getSimpleName());}
        finally {
            if(saved!=null) {
                boolean restored=false;
                try{b.restore(saved);restored=saved.equals(b.state());r.put("stateAfter",values(b.state()));}
                catch(Exception|LinkageError e){r.put("restoreErrorClass",e.getClass().getSimpleName());}
                r.put("stateRestored",restored);if(!restored)r.put("available",false);
            }
        }
        return r;
    }
    private static Map<String,Object> values(State s){return Map.ofEntries(
        Map.entry("readFbo",s.readFbo()),Map.entry("readBuffer",s.readBuffer()),Map.entry("packBuffer",s.packBuffer()),
        Map.entry("alignment",s.alignment()),Map.entry("rowLength",s.rowLength()),Map.entry("imageHeight",s.imageHeight()),
        Map.entry("skipPixels",s.skipPixels()),Map.entry("skipRows",s.skipRows()),Map.entry("skipImages",s.skipImages()),
        Map.entry("swap",s.swap()),Map.entry("lsb",s.lsb()));}
}
