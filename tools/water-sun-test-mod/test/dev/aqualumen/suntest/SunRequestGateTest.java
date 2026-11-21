package dev.aqualumen.suntest;

/** Synthetic UUID/time, never live requests. */
public final class SunRequestGateTest {
    private static String id(int n){return String.format("00000000-0000-0000-0000-%012d",n);}
    private static void require(boolean result,String message){if(!result)throw new AssertionError(message);}
    public static void main(String[] args) {
        SunRequestGate gate=new SunRequestGate();require(gate.claim(id(1),0),"first admitted");
        require(!gate.claim(id(1),2_000_000_000L),"one-shot");require(!gate.claim(id(2),999_999_999),"1Hz");
        for(int i=2;i<=8;i++)require(gate.claim(id(i),(i-1)*1_000_000_000L),"eight spaced");
        require(!gate.claim(id(9),10_000_000_000L),"ninth denied");require(!new SunRequestGate().claim("1-1-1-1-1",0),"canonical UUID");
        System.out.println("PASS synthetic CPU: canonical one-shot UUID, 1Hz, max8");
    }
}
