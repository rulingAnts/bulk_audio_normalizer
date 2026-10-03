"""
Checks used by .github/workflows/build-windows.yml.

  python verify_windows_build.py pe FILE...
      Each FILE is a 64-bit x86-64 Windows executable: PE32+ (optional
      header magic 0x20B) with COFF Machine 0x8664 (IMAGE_FILE_MACHINE_AMD64).
      An ARM64 build (0xAA64) or a 32-bit one fails.

  python verify_windows_build.py size FILE MIN_MB MAX_MB
      FILE's size is within [MIN_MB, MAX_MB] megabytes.

  python verify_windows_build.py bundle EXE NAME=SOURCE...
      PyInstaller's onefile archive inside EXE holds an entry NAME whose
      bytes are identical (SHA-256) to the file SOURCE. Needs PyInstaller.

Standard library only, apart from PyInstaller for "bundle".
"""
import hashlib
import struct
import sys
from pathlib import Path

IMAGE_FILE_MACHINE_AMD64 = 0x8664
PE32_PLUS_MAGIC = 0x20B
MACHINES = {0x14C: 'i386', 0x8664: 'x86-64', 0xAA64: 'ARM64', 0x1C4: 'ARMv7'}


def pe_header(path: Path):
    """(machine, optional-header magic) of a PE file."""
    with open(path, 'rb') as f:
        head = f.read(64 * 1024)
    if head[:2] != b'MZ':
        raise ValueError('no MZ header')
    pe = struct.unpack_from('<I', head, 0x3C)[0]
    if head[pe:pe + 4] != b'PE\0\0':
        raise ValueError('no PE signature')
    machine = struct.unpack_from('<H', head, pe + 4)[0]
    magic = struct.unpack_from('<H', head, pe + 24)[0]
    return machine, magic


def check_pe(files):
    ok = True
    for name in files:
        path = Path(name)
        try:
            machine, magic = pe_header(path)
        except (OSError, ValueError, struct.error) as e:
            print(f'FAIL {path}: {e}')
            ok = False
            continue
        label = MACHINES.get(machine, hex(machine))
        if machine == IMAGE_FILE_MACHINE_AMD64 and magic == PE32_PLUS_MAGIC:
            print(f'ok   {path}: PE32+ {label} (Machine 0x{machine:04X})')
        else:
            print(f'FAIL {path}: Machine 0x{machine:04X} ({label}), optional header magic 0x{magic:X}')
            ok = False
    return ok


def check_size(name, min_mb, max_mb):
    size = Path(name).stat().st_size
    mb = size / (1024 * 1024)
    if float(min_mb) <= mb <= float(max_mb):
        print(f'ok   {name}: {mb:.1f} MB')
        return True
    print(f'FAIL {name}: {mb:.1f} MB, expected {min_mb}-{max_mb} MB')
    return False


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_bundle(exe, pairs):
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(exe))
    # Entry names use the build machine's separator; compare with '/'.
    names = {n.replace('\\', '/'): n for n in archive.toc}
    ok = True
    for pair in pairs:
        dest, _, source = pair.partition('=')
        dest = dest.replace('\\', '/')
        if dest not in names:
            print(f'FAIL {exe}: no archive entry {dest!r}')
            ok = False
            continue
        packed = archive.extract(names[dest])
        expected = Path(source).read_bytes()
        if sha256(packed) == sha256(expected):
            print(f'ok   {exe}: {dest} ({len(packed) / (1024 * 1024):.1f} MB, sha256 {sha256(packed)[:16]}...)')
        else:
            print(f'FAIL {exe}: {dest} differs from {source}')
            ok = False
    return ok


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, args = argv[1], argv[2:]
    if cmd == 'pe' and args:
        ok = check_pe(args)
    elif cmd == 'size' and len(args) == 3:
        ok = check_size(*args)
    elif cmd == 'bundle' and len(args) >= 2:
        ok = check_bundle(args[0], args[1:])
    else:
        print(__doc__)
        return 2
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
