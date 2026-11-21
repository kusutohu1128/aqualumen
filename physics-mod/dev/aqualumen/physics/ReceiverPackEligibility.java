package dev.aqualumen.physics;

public final class ReceiverPackEligibility {
    private String approvedName;

    public boolean accepts(String currentName) {
        if(currentName==null) return false;
        if(currentName==approvedName) return true;
        if(!currentName.startsWith("Aqualumen")) return false;
        approvedName=currentName;
        return true;
    }
}
