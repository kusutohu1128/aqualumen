package dev.aqualumen.physics;

public final class ReceiverPackEligibilityTest {
    public static void main(String[] arguments) {
        var eligibility=new ReceiverPackEligibility();
        String approved=new String("Aqualumen-Test");
        for(int repeat=0;repeat<1000;repeat++) {
            for(String name:new String[]{approved,approved,new String(approved),
                    "Complementary",null,"","aqualumen","OtherAqualumen",
                    "Aqualumen","Aqualumen-Next",approved}) {
                boolean expected=name!=null && name.startsWith("Aqualumen");
                if(eligibility.accepts(name)!=expected)
                    throw new AssertionError("Pack eligibility differs from fresh prefix predicate");
            }
        }
        System.out.println("PASS pack eligibility: 11000 same-object/new-object/switch/null prefix comparisons; CPU only");
    }
}
