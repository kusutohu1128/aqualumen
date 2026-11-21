package dev.aqualumen.stageprobe;

/** Synthetic CPU request ids/clock, not runtime observations. */
public final class RequestGateTest {
    private static String id(int value){return String.format("00000000-0000-0000-0000-%012d",value);}
    private static void require(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args) {
        RequestGate gate=new RequestGate();
        require(gate.claim(id(1),0),"First eligible canonical request must be admitted");
        require(!gate.claim(id(1),1_000_000_000L),"A request must be one-shot even after the interval");
        require(!gate.claim(id(2),999_999_999L),"A new request must not bypass the 1 Hz limit");
        for(int i=2;i<=8;i++)require(gate.claim(id(i),(i-1)*1_000_000_000L),"Eight eligible spaced requests are permitted");
        require(!gate.claim(id(9),20_000_000_000L),"No ninth attempt is allowed in this JVM");
        require(!new RequestGate().claim("1-1-1-1-1",0),"Noncanonical UUID must be rejected");
        System.out.println("PASS synthetic CPU: canonical, one-shot, 1 Hz, eight-attempt request boundary");
    }
}
