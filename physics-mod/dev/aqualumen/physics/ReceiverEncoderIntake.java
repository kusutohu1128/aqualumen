package dev.aqualumen.physics;

import java.util.ArrayList;
import org.lwjgl.system.MemoryUtil;

public final class ReceiverEncoderIntake {
    private record Write(ReceiverSodiumScope scope, long pointer, int stride) { }
    private static final ThreadLocal<Write> pending = new ThreadLocal<>();
    private ReceiverEncoderIntake() { }

    public static void begin(long pointer, int stride) {
        var scope = ReceiverSodiumScope.current();
        if (scope == null || !scope.wantsEncoding()) return;
        var previous = pending.get();
        if (previous != null && previous.scope() != scope) pending.remove();
        if (pending.get() != null || pointer == 0 || stride < 20 || stride > 128 || stride % 4 != 0) {
            pending.remove(); scope.reject("Owned encoder pointer/stride unavailable"); return;
        }
        pending.set(new Write(scope,pointer,stride));
    }

    public static void end(long returned) {
        var write = pending.get(); pending.remove();
        if (write == null || ReceiverSodiumScope.current() != write.scope()) return;
        if (returned != write.pointer() + 4L * write.stride()) {
            write.scope().reject("Owned encoder returned an unexpected extent"); return;
        }
        var packed = new ArrayList<ReceiverVertexShader.Encoded>();
        for (int index = 0; index < 4; index++) {
            long pointer = write.pointer() + (long)index * write.stride();
            packed.add(new ReceiverVertexShader.Encoded(MemoryUtil.memGetInt(pointer+8),
                    MemoryUtil.memGetInt(pointer+12),MemoryUtil.memGetInt(pointer+16)));
        }
        write.scope().encoded(write.stride(),packed);
    }
}
