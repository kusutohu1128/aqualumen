"""Independent byte-decoding and ideal atlas-coordinate contracts, no GPU claim."""
import struct
import unittest
import zlib
from water_coast_attribution_image import decode, atlas_point


def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))


class AtlasDecodeTest(unittest.TestCase):
    def test_all_five_filters_rgb_and_rgba(self):
        for channels,color in ((3,2),(4,6)):
            w,h=5,5
            source=bytes((i*71+37)&255 for i in range(w*h*channels))
            stride=w*channels
            encoded=bytearray()
            for y in range(h):
                encoded.append(y)
                for x in range(stride):
                    index=y*stride+x
                    a=source[index-channels] if x>=channels else 0
                    b=source[index-stride] if y else 0
                    c=source[index-stride-channels] if y and x>=channels else 0
                    p=a+b-c
                    # Independent conditional tie selection, not the decoder helper.
                    pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                    pp=a if pa<=pb and pa<=pc else b if pb<=pc else c
                    predictor=(0,a,b,(a+b)//2,pp)[y]
                    encoded.append((source[index]-predictor)&255)
            png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,color,0,0,0))
            png+=chunk(b'IDAT',zlib.compress(encoded))+chunk(b'IEND',b'')
            result,actual=decode(png,(w,h))
            self.assertEqual(bytes(result),source)
            self.assertEqual(actual,channels)

    def test_top_and_bottom_ideal_gl_pixel_center_mapping(self):
        self.assertEqual(atlas_point(0,0),[1,1439])
        self.assertEqual(atlas_point(1279,719),[2559,1])
        self.assertEqual(atlas_point(442,564),[885,311])


if __name__=='__main__':
    unittest.main()
