#!/usr/bin/env python3
"""Exit 0 if two thin 64-bit Mach-O files are the same program apart from their code signature.

Usage: same_macho.py A B   (run "codesign --remove-signature" on copies of both first)

PyInstaller re-signs every binary it bundles (ad hoc), so a bundled ffmpeg is never
byte-identical to the one that was built. Once both signatures are removed, the only
difference left is the __LINKEDIT segment's vmsize, which codesign rounds differently.
This compares the files with that one field zeroed, so any other change (code, data,
load commands, linked libraries) still counts as a difference.
"""
import struct
import sys

MH_MAGIC_64 = 0xFEEDFACF
LC_SEGMENT_64 = 0x19


def normalized(path):
    data = bytearray(open(path, 'rb').read())
    magic, _cpu, _sub, _ftype, ncmds, _size, _flags, _res = struct.unpack_from('<IiiIIIII', data, 0)
    if magic != MH_MAGIC_64:
        sys.exit(f'{path}: not a thin 64-bit Mach-O file')
    offset = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from('<II', data, offset)
        if cmd == LC_SEGMENT_64 and data[offset + 8:offset + 24].rstrip(b'\0') == b'__LINKEDIT':
            struct.pack_into('<Q', data, offset + 32, 0)  # vmsize
        offset += cmdsize
    return bytes(data)


def main():
    a, b = sys.argv[1], sys.argv[2]
    if normalized(a) != normalized(b):
        print(f'{a} and {b} differ')
        return 1
    print(f'{a} and {b} are the same program (signatures aside)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
