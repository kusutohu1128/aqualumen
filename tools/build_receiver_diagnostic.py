"""Create an opt-in receiver-outcome diagnostic pack without changing sources."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Diagnostic shader anchor is not unique: '+before)
    return source.replace(before, after, 1)


def replace_final_guard(source, replacement):
    before, marker, trailing = source.rpartition('\n#endif')
    if not marker or trailing.strip():
        raise ValueError('Receiver header closing guard is not terminal')
    return before+replacement+trailing


def diagnostic_shader(source):
    source = replace_once(source, '    vec4 reflectedHit=reflectionTrace(',
        '    vec3 receiverDiagnostic=vec3(1.0,0.0,1.0);\n'
        '    vec4 reflectedHit=reflectionTrace(')
    source = replace_once(source,
        '    if (underwater && reflectedHit.a<=0.0 && (aqualumenReceiverReady==1 || aqualumenReceiverReady==2)) {',
        '    if (reflectedHit.a>0.0) receiverDiagnostic=vec3(0.0,0.0,1.0);\n'
        '    if (underwater && reflectedHit.a<=0.0 && (aqualumenReceiverReady==1 || aqualumenReceiverReady==2)) {\n'
        '        receiverDiagnostic=vec3(1.0,0.0,0.0);')
    source = replace_once(source, '        if (reflectedReceiver.sourceReady) {',
        '        if (reflectedReceiver.known) receiverDiagnostic=vec3(1.0,1.0,0.0);\n'
        '        if (reflectedReceiver.sourceReady) {\n'
        '            receiverDiagnostic=vec3(0.0,1.0,0.0);')
    return replace_once(source, '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);',
        '    if (underwater) color=fresnel>=0.9999?receiverDiagnostic:vec3(0.05);\n'
        '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);')


def rejection_shader(source):
    expected = 'e3a88fb2b0b579b624eae3cf3d00aa0707c6b34d30b4c94c76ba8dfd213fadaa'
    if hashlib.sha256(source.encode()).hexdigest() != expected:
        raise ValueError('Receiver rejection instrumentation requires the pinned v33 source')
    marker = 'WaterReceiver waterReceiverFirstImpl(vec3 origin,vec3 direction,bool interfaceGeometry) {'
    source = replace_once(source, marker, 'int aqualumenDiagnosticReason=0;\n'+marker+'\n    aqualumenDiagnosticReason=0;')
    pieces = source.split('return result;')
    if len(pieces) != 23:
        raise ValueError('Unexpected receiver return count')
    source = pieces[0]
    for reason, remainder in enumerate(pieces[1:], 1):
        source += '{aqualumenDiagnosticReason='+str(reason)+';return result;}'+remainder
    source = replace_once(source,
        '                if(!interfaceGeometry || !waterReceiverSurfaceCorners(cell,geometry,heights)\n'
        '                    || !waterReceiverBelowBoth(local+direction*travel-vec3(cell),local+direction*next-vec3(cell),heights)){aqualumenDiagnosticReason=19;return result;}',
        '                if(!interfaceGeometry){aqualumenDiagnosticReason=31;return result;}\n'
        '                if(!waterReceiverSurfaceCorners(cell,geometry,heights)){aqualumenDiagnosticReason=32;return result;}\n'
        '                if(!waterReceiverBelowBoth(local+direction*travel-vec3(cell),local+direction*next-vec3(cell),heights)){aqualumenDiagnosticReason=33;return result;}')
    return replace_once(source, '\n#endif',
        '\nvec3 aqualumenDiagnosticRejectionColor() {\n'
        '    if(aqualumenDiagnosticReason==5)return vec3(1.0,0.0,0.0);\n'
        '    if(aqualumenDiagnosticReason==17)return vec3(1.0,0.35,0.0);\n'
        '    if(aqualumenDiagnosticReason==14)return vec3(0.0,0.0,1.0);\n'
        '    if(aqualumenDiagnosticReason==33)return vec3(0.0,1.0,1.0);\n'
        '    if(aqualumenDiagnosticReason==32)return vec3(1.0,1.0,0.0);\n'
        '    if(aqualumenDiagnosticReason==3 || aqualumenDiagnosticReason==31)return vec3(1.0,0.0,1.0);\n'
        '    return vec3(1.0);\n'
        '}\n#endif')


def run_rejection_shader(source):
    expected = {'af98491f4669ef591d99b1d942402678dd84f654ac9c72e18f48eef81a2a3ad5',
                '0479d301bf8af5c19386e0e548ae618af258a1d81686c265169105614d9776a8',
                '6c21e0b7502b300308a4f34b902be17556b233f6f71e986628702f8eee91a744'}
    if hashlib.sha256(source.encode()).hexdigest() not in expected:
        raise ValueError('Run receiver instrumentation requires the pinned wide-field source')
    marker = 'WaterReceiver waterReceiverFirstImpl(vec3 origin,vec3 direction,bool interfaceGeometry) {'
    source = replace_once(source, marker, 'int aqualumenDiagnosticReason=0;\n'+marker+'\n    aqualumenDiagnosticReason=0;')
    pieces = source.split('return result;')
    if len(pieces) != 26:
        raise ValueError('Unexpected run receiver return count')
    source = pieces[0]
    for reason, remainder in enumerate(pieces[1:], 1):
        source += '{aqualumenDiagnosticReason='+str(reason)+';return result;}'+remainder
    source = replace_once(source,
        '                if(face.a!=1.0 || any(notEqual(face.xyz,normal))){aqualumenDiagnosticReason=11;return result;}',
        '                if(face.a!=1.0){aqualumenDiagnosticReason=41;return result;}\n'
        '                if(any(notEqual(face.xyz,normal))){aqualumenDiagnosticReason=42;return result;}')
    source = replace_once(source,
        '                if(!interfaceGeometry || !waterReceiverSurfaceCorners(cell,geometry,heights)\n'
        '                    || !waterReceiverBelowBoth(local+direction*travel-vec3(cell),local+direction*next-vec3(cell),heights)){aqualumenDiagnosticReason=22;return result;}',
        '                if(!interfaceGeometry){aqualumenDiagnosticReason=31;return result;}\n'
        '                if(!waterReceiverSurfaceCorners(cell,geometry,heights)){aqualumenDiagnosticReason=32;return result;}\n'
        '                if(!waterReceiverBelowBoth(local+direction*travel-vec3(cell),local+direction*next-vec3(cell),heights)){aqualumenDiagnosticReason=33;return result;}')
    return replace_final_guard(source,
        '\nvec3 aqualumenDiagnosticRejectionColor() {\n'
        '    if(aqualumenDiagnosticReason==6)return vec3(1.0,0.0,0.0);\n'
        '    if(aqualumenDiagnosticReason==20)return vec3(1.0,0.35,0.0);\n'
        '    if(aqualumenDiagnosticReason==17)return vec3(0.0,0.0,1.0);\n'
        '    if(aqualumenDiagnosticReason==33)return vec3(0.0,1.0,1.0);\n'
        '    if(aqualumenDiagnosticReason==32)return vec3(1.0,1.0,0.0);\n'
        '    if(aqualumenDiagnosticReason==9)return vec3(0.6,0.0,0.9);\n'
        '    if(aqualumenDiagnosticReason==42)return vec3(1.0);\n'
        '    if(aqualumenDiagnosticReason==41 || aqualumenDiagnosticReason==13 || aqualumenDiagnosticReason==14)return vec3(1.0,0.0,0.5);\n'
        '    if(aqualumenDiagnosticReason==7)return vec3(1.0,0.0,1.0);\n'
        '    if(aqualumenDiagnosticReason==5 || aqualumenDiagnosticReason==23)return vec3(0.35);\n'
        '    return vec3(1.0,0.8,0.4);\n'
        '}\n#endif')


def unknown_rejection_shader(source):
    source = run_rejection_shader(source)
    source = replace_once(source, 'int aqualumenDiagnosticReason=0;',
        'float aqualumenDiagnosticUnknownKind=0.0;\nint aqualumenDiagnosticReason=0;')
    source = replace_once(source, '    aqualumenDiagnosticReason=0;',
        '    aqualumenDiagnosticUnknownKind=0.0;\n    aqualumenDiagnosticReason=0;')
    source = replace_once(source,
        'if(kind!=2.0 && kind!=4.0 && kind!=5.0){aqualumenDiagnosticReason=17;return result;}',
        'if(kind!=2.0 && kind!=4.0 && kind!=5.0){aqualumenDiagnosticUnknownKind=geometry.g;aqualumenDiagnosticReason=17;return result;}')
    marker = '\nvec3 aqualumenDiagnosticRejectionColor() {'
    if source.count(marker) != 1:
        raise ValueError('Unknown-kind palette anchor is not unique')
    start = source.index(marker)
    end = source.rindex('\n#endif')
    return source[:start]+(
        '\nvec3 aqualumenDiagnosticRejectionColor() {\n'
        '    if(aqualumenDiagnosticReason!=17)return vec3(0.1);\n'
        '    if(aqualumenDiagnosticUnknownKind==1.0)return vec3(1.0,0.0,0.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==2.0)return vec3(0.8,0.0,0.4);\n'
        '    if(aqualumenDiagnosticUnknownKind==3.0)return vec3(0.0,0.0,1.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==4.0)return vec3(1.0,1.0,0.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==5.0)return vec3(1.0,0.35,0.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==6.0)return vec3(1.0,0.0,1.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==7.0)return vec3(1.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==8.0)return vec3(0.0,1.0,1.0);\n'
        '    if(aqualumenDiagnosticUnknownKind==9.0)return vec3(0.6,0.0,0.9);\n'
        '    return vec3(0.4);\n'
        '}')+source[end:]


def interface_shader(source, exit_rays=False):
    return replace_once(source, '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);',
        '    if (underwater) {\n'
        '        bool transmittedValid=dot(transmitted,transmitted)>0.000001;\n'
        '        float reflectedSide=dot(reflected,geometricNormal);\n'
        '        float transmittedSide=dot(transmitted,geometricNormal);\n'
        '        color=vec3(0.0,0.5,0.0);\n'
        '        if (!transmittedValid) color=vec3(0.0,0.0,0.5);\n'
        '        if (transmittedValid && transmittedSide>0.00001) color=vec3(1.0,0.35,0.0);\n'
        '        if (reflectedSide < -0.00001) color=vec3(1.0,0.0,0.0);\n'
        + ('        if (transmittedValid && transmittedSide<=0.00001 && reflectedSide>=-0.00001\n'
           '            && transmitted.y < -0.00001) color=vec3(1.0,1.0,0.0);\n' if exit_rays else '') +
        '    }\n'
        '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);')


def build(source, target, rejections=False, run_rejections=False, unknown_kinds=False, interface=False, exit_rays=False,
          raw_interface=False, interface_normal=False, raw_receiver=False):
    if sum((rejections, run_rejections, unknown_kinds, interface, exit_rays)) > 1:
        raise ValueError('Choose exactly one receiver instrumentation revision')
    if raw_interface and not (interface or exit_rays):
        raise ValueError('Raw interface readout requires an interface diagnostic')
    if raw_receiver and (interface or exit_rays or raw_interface):
        raise ValueError('Raw receiver readout requires receiver-only instrumentation')
    if interface_normal and not (interface or exit_rays):
        raise ValueError('Interface normal comparison requires an interface diagnostic')
    with ZipFile(source) as archive:
        original = archive.read('shaders/gbuffers_water.fsh').decode()
        if interface_normal:
            if '#ifdef AQUALUMEN_INTERFACE_NORMAL_COMPARISON' not in original:
                raise ValueError('Missing coupled interface normal comparison hook')
            original = replace_once(original, '#version 330 compatibility',
                                    '#version 330 compatibility\n#define AQUALUMEN_INTERFACE_NORMAL_COMPARISON')
        shader = interface_shader(original,exit_rays) if interface or exit_rays else diagnostic_shader(original)
        final = None
        if raw_interface or raw_receiver:
            for entry in archive.infolist():
                if entry.filename.endswith(('.fsh','.vsh','.glsl','.properties')) and b'colortex12' in archive.read(entry.filename):
                    raise ValueError('Diagnostic target colortex12 is already owned')
            archive.getinfo('shaders/final.fsh')
            shader = replace_once(shader,'/* DRAWBUFFERS:0 */',
                '/* RENDERTARGETS:0,12 */\n/* const int colortex12Format = RGBA8; */\n'
                'const bool colortex12Clear = true;\nconst vec4 colortex12ClearColor = vec4(0.0,0.0,0.0,0.0);')
            shader = replace_once(shader,'    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);',
                '    gl_FragData[0]=vec4(max(color,vec3(0.0)),1.0);\n'
                '    gl_FragData[1]=underwater?vec4(color,1.0):vec4(0.0);')
            final = ('#version 330 compatibility\nuniform sampler2D colortex12;\n'
                     'void main(){vec4 raw=texelFetch(colortex12,ivec2(gl_FragCoord.xy),0);\n'
                     'gl_FragColor=vec4(raw.a>=0.999?raw.rgb:vec3(0.0),1.0);}\n').encode()
        receiver = None
        if rejections or run_rejections or unknown_kinds:
            instrument = unknown_rejection_shader if unknown_kinds else run_rejection_shader if run_rejections else rejection_shader
            receiver = instrument(archive.read('shaders/lib/water_receiver.glsl').decode())
            shader = replace_once(shader, '        if (reflectedReceiver.known) receiverDiagnostic=vec3(1.0,1.0,0.0);',
                '        if (!reflectedReceiver.sourceReady) receiverDiagnostic=aqualumenDiagnosticRejectionColor();')
            shader = replace_once(shader, 'if (reflectedHit.a>0.0) receiverDiagnostic=vec3(0.0,0.0,1.0);',
                'if (reflectedHit.a>0.0) receiverDiagnostic=vec3(0.4,0.4,1.0);')
        with ZipFile(target, 'x') as output:
            for entry in archive.infolist():
                blob = shader.encode() if entry.filename == 'shaders/gbuffers_water.fsh' else archive.read(entry.filename)
                if receiver is not None and entry.filename == 'shaders/lib/water_receiver.glsl':
                    blob = receiver.encode()
                if final is not None and entry.filename == 'shaders/final.fsh':
                    blob = final
                output.writestr(entry, blob)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--rejections', action='store_true')
    modes.add_argument('--run-rejections', action='store_true')
    modes.add_argument('--unknown-kinds', action='store_true')
    modes.add_argument('--interface', action='store_true')
    modes.add_argument('--exit-rays', action='store_true')
    parser.add_argument('--raw-interface', action='store_true')
    parser.add_argument('--interface-normal', action='store_true')
    parser.add_argument('--raw-receiver', action='store_true')
    arguments = parser.parse_args()
    build(arguments.source, arguments.target, arguments.rejections, arguments.run_rejections, arguments.unknown_kinds,
          arguments.interface, arguments.exit_rays, arguments.raw_interface, arguments.interface_normal, arguments.raw_receiver)
    print(arguments.target)
