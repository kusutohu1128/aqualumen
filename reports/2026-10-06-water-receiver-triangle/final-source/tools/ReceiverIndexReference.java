import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import net.caffeinemc.mods.sodium.client.render.chunk.SharedQuadIndexBuffer;

/** Invoke only the installed public CPU index generator; no GL/context/Minecraft. */
public final class ReceiverIndexReference {
    public static void main(String[] args) {
        System.out.print("{");
        for (var type : SharedQuadIndexBuffer.IndexType.values()) {
            var buffer = ByteBuffer.allocate(14*6*type.getBytesPerElement()).order(ByteOrder.LITTLE_ENDIAN);
            type.createIndexBuffer(buffer,14);
            int[] values = new int[84];
            for (int i=0;i<84;i++) values[i] = type.getBytesPerElement()==2 ? buffer.getShort(i*2)&65535 : buffer.getInt(i*4);
            if(type.ordinal()!=0) System.out.print(",");
            System.out.print("\""+type.name()+"\":"+Arrays.toString(values));
        }
        System.out.println("}");
    }
}
