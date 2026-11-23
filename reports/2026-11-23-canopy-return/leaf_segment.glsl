if(shape==2 && !towardSun) {
                float straight=exp(-1.45*(end-t));
#ifdef LAMP_LEAF_RETURN
                // The former ballistic ray still reaches any solid behind the leaves.
                // Add only the intercepted fraction of the lit, sprite-covered leaf.
                if(i>0) {
                    int entryFace=2*axis+int(ray[axis]<0.);
                    vec3 outgoing=texelFetch(aqualumenBounceExit,2*bounceAddress(cell,entryFace),0).rgb;
                    float fade=1.-smoothstep(9.,bounceReach,t);
                    hit.leafRadiance+=through*(1.-straight)*outgoing*fade;
                }
#endif
                through*=straight;
            }
