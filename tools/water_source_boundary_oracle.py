"""Independent geometry oracle; explicitly not the GLSL SSR march.

Raw origin/ray remain unnormalized. Finite observed planar-depth fixture only,
not a claim about arbitrary Minecraft world/hidden/offscreen geometry.
"""
import math


def first_plane(origin,ray,projection,distance):
    if len(origin)!=3 or len(ray)!=3 or len(projection)!=16:
        raise ValueError('Explicit view vectors and column-major matrix required')
    if not all(math.isfinite(x) for x in (*origin,*ray,*projection,distance)) or distance<=0:
        raise ValueError('Finite positive scene distance required')
    if ray[2]==0:
        return dict(kind='no-forward-crossing')
    travel=(-distance-origin[2])/ray[2]
    if travel<=0:
        return dict(kind='no-forward-crossing',travel=travel)
    position=tuple(a+travel*b for a,b in zip(origin,ray))
    homogeneous=(*position,1.)
    clip=tuple(math.fsum(projection[k*4+j]*homogeneous[k] for k in range(4)) for j in range(4))
    if clip[3]<=0:
        return dict(kind='behind-camera',travel=travel,position=position)
    screen=tuple(.5*clip[i]/clip[3]+.5 for i in range(2))
    in_full=all(0<=a<=1 for a in screen)
    in_safe=all(.002<=a<=.998 for a in screen)
    return dict(kind='observed-plane' if in_safe else 'viewport-margin' if in_full else 'outside-observed-viewport',
        travel=travel,distance=travel*math.sqrt(math.fsum(a*a for a in ray)),
        position=position,screen=screen,inFullViewport=in_full,inTraceViewport=in_safe)
