#version 330 compatibility
#ifndef AQUALUMEN_WATER_SUN_PREPARED_GLSL
#define AQUALUMEN_WATER_SUN_PREPARED_GLSL
// TEST pure certificate only. No shipping caller. Endpoints are exact signed
// integers scaled by 2^-24; all arithmetic below is integer, not float math.
// No extension/precise/FP64 rounding assumption. Raw inputs are decoded bits.
// 0: certified absent prescribed branch; 1: certified supported; -1: unknown.
struct WSPInterval { int lo; int hi; bool valid; };
struct WSPWide { uint lo; uint hi; };

WSPInterval WSP_interval(int lo, int hi) {
    WSPInterval r;
    r.valid = lo >= -1073741823 && hi <= 1073741823 && lo <= hi;
    r.lo = r.valid ? lo : 0;
    r.hi = r.valid ? hi : 0;
    return r;
}
WSPInterval WSP_unknown() {
    WSPInterval r; r.lo = 0; r.hi = 0; r.valid = false; return r;
}
WSPInterval WSP_point(float raw) {
    uint bits = floatBitsToUint(raw);
    uint magnitude = bits & 0x7fffffffu;
    uint exponent = magnitude >> 23u;
    if (magnitude > 0x40000000u || (exponent == 0u && magnitude != 0u))
        return WSP_unknown(); // |raw|>2, nonfinite, or subnormal: unknown.
    if (magnitude == 0u) return WSP_interval(0, 0);
    uint mantissa = (magnitude & 0x007fffffu) | 0x00800000u;
    uint quotient;
    uint remainder = 0u;
    if (exponent >= 126u) {
        quotient = mantissa << (exponent - 126u); // shift <=2 by domain.
    } else {
        uint shift = 126u - exponent;
        if (shift >= 24u) { quotient = 0u; remainder = mantissa; }
        else {
            quotient = mantissa >> shift;
            remainder = mantissa & ((1u << shift) - 1u);
        }
    }
    int floorValue = int(quotient);
    int ceilingValue = floorValue + (remainder != 0u ? 1 : 0);
    return (bits & 0x80000000u) != 0u
        ? WSP_interval(-ceilingValue, -floorValue)
        : WSP_interval(floorValue, ceilingValue);
}
WSPInterval WSP_add(WSPInterval a, WSPInterval b) {
    if (!a.valid || !b.valid) return WSP_unknown();
    // Each endpoint is bounded by 2^30-1, so these sums cannot overflow int32.
    return WSP_interval(a.lo + b.lo, a.hi + b.hi);
}
WSPInterval WSP_sub(WSPInterval a, WSPInterval b) {
    if (!a.valid || !b.valid) return WSP_unknown();
    return WSP_interval(a.lo - b.hi, a.hi - b.lo);
}
WSPWide WSP_multiplyWide(uint a, uint b) {
    uint a0 = a & 0xffffu, a1 = a >> 16u;
    uint b0 = b & 0xffffu, b1 = b >> 16u;
    uint p0 = a0*b0, p1 = a0*b1, p2 = a1*b0, p3 = a1*b1;
    uint lo1 = p0 + (p1 << 16u);
    uint carry1 = lo1 < p0 ? 1u : 0u;
    uint lo2 = lo1 + (p2 << 16u);
    uint carry2 = lo2 < lo1 ? 1u : 0u;
    WSPWide r;
    r.lo = lo2;
    r.hi = p3 + (p1 >> 16u) + (p2 >> 16u) + carry1 + carry2;
    return r;
}
WSPInterval WSP_product(int a, int b) {
    // Negation is safe: neither argument is INT_MIN, by endpoint invariant.
    uint aa = uint(a < 0 ? -a : a), bb = uint(b < 0 ? -b : b);
    WSPWide p = WSP_multiplyWide(aa, bb);
    if (p.hi >= 0x00400000u) return WSP_unknown(); // quotient >=2^30.
    uint q = (p.hi << 8u) | (p.lo >> 24u);
    uint remainder = p.lo & 0x00ffffffu;
    int floorValue = int(q);
    int ceilingValue = floorValue + (remainder != 0u ? 1 : 0);
    return (a < 0) != (b < 0)
        ? WSP_interval(-ceilingValue, -floorValue)
        : WSP_interval(floorValue, ceilingValue);
}
WSPInterval WSP_mul(WSPInterval a, WSPInterval b) {
    if (!a.valid || !b.valid) return WSP_unknown();
    WSPInterval p0 = WSP_product(a.lo, b.lo);
    WSPInterval p1 = WSP_product(a.lo, b.hi);
    WSPInterval p2 = WSP_product(a.hi, b.lo);
    WSPInterval p3 = WSP_product(a.hi, b.hi);
    if (!p0.valid || !p1.valid || !p2.valid || !p3.valid) return WSP_unknown();
    int lo = p0.lo, hi = p0.hi;
    if (p1.lo < lo) lo = p1.lo;
    if (p2.lo < lo) lo = p2.lo;
    if (p3.lo < lo) lo = p3.lo;
    if (p1.hi > hi) hi = p1.hi;
    if (p2.hi > hi) hi = p2.hi;
    if (p3.hi > hi) hi = p3.hi;
    return WSP_interval(lo, hi);
}

// Standalone CPU-only candidate. Original integer primitives above are literal.
// Cache is LOCAL to one fragment/cap invocation, never shared across pixels.
// No pack includes this file; native speed/identity remain unqualified.
struct WSPViewContext {
    WSPInterval vx;
    WSPInterval vy;
    WSPInterval vz;
    WSPInterval E;
    WSPInterval K2;
    WSPInterval downScale;
    bool valid;
};

WSPViewContext waterSunSupportPrepareView(vec3 rawV, float eta) {
    WSPViewContext c;
    c.vx = WSP_point(rawV.x);
    c.vy = WSP_point(rawV.y);
    c.vz = WSP_point(rawV.z);
    WSPInterval e = WSP_point(eta);
    WSPInterval one = WSP_interval(16777216, 16777216);
    c.E = WSP_mul(e, e);
    WSPInterval V = WSP_add(WSP_add(WSP_mul(c.vx, c.vx), WSP_mul(c.vy, c.vy)), WSP_mul(c.vz, c.vz));
    c.K2 = WSP_add(one, WSP_mul(c.E, WSP_sub(V, one)));
    // Keep the original downRight inner tree; no interval square shortcut.
    c.downScale = WSP_mul(c.E, WSP_mul(c.vy, c.vy));
    uint vY = floatBitsToUint(rawV.y), eBits = floatBitsToUint(eta);
    c.valid = c.vx.valid && c.vy.valid && c.vz.valid && e.valid
        && (vY & 0x80000000u) != 0u && (vY & 0x7fffffffu) != 0u
        && eBits > 0x3f800000u && eBits <= 0x40000000u
        && c.E.valid && V.valid && c.K2.valid && c.downScale.valid
        && V.lo > 0 && c.K2.lo > 0;
    return c;
}

int waterSunSupportClassPrepared(WSPViewContext c, vec3 rawTarget) {
    WSPInterval tx = WSP_point(rawTarget.x), ty = WSP_point(rawTarget.y), tz = WSP_point(rawTarget.z);
    if (!c.valid || !tx.valid || !ty.valid || !tz.valid) return -1;
    uint tY = floatBitsToUint(rawTarget.y);
    if ((tY & 0x80000000u) != 0u || (tY & 0x7fffffffu) == 0u) return -1;
    WSPInterval U = WSP_add(WSP_add(WSP_mul(tx, tx), WSP_mul(ty, ty)), WSP_mul(tz, tz));
    WSPInterval B = WSP_add(WSP_add(WSP_mul(c.vx, tx), WSP_mul(c.vy, ty)), WSP_mul(c.vz, tz));
    if (!U.valid || !B.valid || U.lo <= 0) return -1;
    WSPInterval downLeft = WSP_mul(c.K2, WSP_mul(ty, ty));
    WSPInterval downRight = WSP_mul(c.downScale, U);
    WSPInterval forwardLeft = WSP_mul(c.K2, U);
    WSPInterval forwardRight = WSP_mul(c.E, WSP_mul(B, B));
    if (!downLeft.valid || !downRight.valid || !forwardLeft.valid || !forwardRight.valid)
        return -1;
    bool downYes = downLeft.hi < downRight.lo;
    bool downNo = downLeft.lo > downRight.hi;
    bool forwardYes = forwardLeft.hi < forwardRight.lo;
    bool forwardNo = forwardLeft.lo > forwardRight.hi;
    bool bNegative = B.hi < 0, bPositive = B.lo > 0;
    // Identical strict separation: no narrowing of unknown/equality/overlap.
    if ((!downYes && !downNo) || (!forwardYes && !forwardNo)
        || (!bNegative && !bPositive)) return -1;
    if (downNo || bPositive || forwardNo) return 0;
    return 1;
}

int waterSunSupportClass(vec3 rawV, vec3 rawTarget, float eta) {
    return waterSunSupportClassPrepared(waterSunSupportPrepareView(rawV, eta), rawTarget);
}
#endif

uniform uvec3 wspViewBits; uniform uvec3 wspTargets[48]; uniform uint wspEtaBits;
uniform int wspCount; uniform int wspSelected;
layout(location=0) out uvec4 wsp0;
layout(location=1) out uvec4 wsp1;
layout(location=2) out uvec4 wsp2;
layout(location=3) out uvec4 wsp3;
layout(location=4) out uvec4 wsp4;
layout(location=5) out uvec4 wsp5;
layout(location=6) out uvec4 wsp6;
layout(location=7) out uvec4 wsp7;
void main(){vec3 v=uintBitsToFloat(wspViewBits);float eta=uintBitsToFloat(wspEtaBits);
WSPViewContext context=waterSunSupportPrepareView(v,eta);
int selectedClass=-2;uint checksum=0u;
for (int node=0;node<wspCount;++node){
vec3 t=uintBitsToFloat(wspTargets[node]);int c=waterSunSupportClassPrepared(context,t);
checksum+=uint(c+1)*uint(node+1);if(node==wspSelected)selectedClass=c;}
wsp0=uvec4(uint(selectedClass+1),floatBitsToUint(v));
wsp1=uvec4(floatBitsToUint(uintBitsToFloat(wspTargets[wspSelected])),floatBitsToUint(eta));
wsp2=uvec4(uint(context.vx.lo),uint(context.vx.hi),uint(context.vx.valid),checksum);
wsp3=uvec4(uint(context.vy.lo),uint(context.vy.hi),uint(context.vy.valid),uint(wspCount));
wsp4=uvec4(uint(context.vz.lo),uint(context.vz.hi),uint(context.vz.valid),uint(context.valid));
wsp5=uvec4(uint(context.E.lo),uint(context.E.hi),uint(context.E.valid),0u);
wsp6=uvec4(uint(context.K2.lo),uint(context.K2.hi),uint(context.K2.valid),0u);
wsp7=uvec4(uint(context.downScale.lo),uint(context.downScale.hi),uint(context.downScale.valid),0u);
}
