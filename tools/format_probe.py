"""Read-only format probe for common executable and package formats.

This is inspection, not function-level diffing. It identifies structure,
architectures, sections, symbol tables and package contents without executing
the target.
"""
import os
import struct
import tempfile
import zipfile
from pathlib import Path


def _u16(b, o, endian="<"):
    return struct.unpack_from(endian + "H", b, o)[0]


def _u32(b, o, endian="<"):
    return struct.unpack_from(endian + "I", b, o)[0]


def _u64(b, o, endian="<"):
    return struct.unpack_from(endian + "Q", b, o)[0]


def _cstr(b, o, limit=200):
    end = b.find(b"\0", o)
    if end < 0:
        end = min(len(b), o + limit)
    return b[o:end].decode("latin-1", "replace")


def _elf(path: Path, head: bytes):
    if len(head) < 52:
        return {"format": "ELF", "error": "truncated header"}
    ei_class = head[4]
    ei_data = head[5]
    endian = "<" if ei_data == 1 else ">"
    is64 = ei_class == 2
    e_type = _u16(head, 16, endian)
    e_machine = _u16(head, 18, endian)
    if is64:
        e_entry = _u64(head, 24, endian)
        e_phoff = _u64(head, 32, endian)
        e_shoff = _u64(head, 40, endian)
        e_phentsize = _u16(head, 54, endian)
        e_phnum = _u16(head, 56, endian)
        e_shentsize = _u16(head, 58, endian)
        e_shnum = _u16(head, 60, endian)
        e_shstrndx = _u16(head, 62, endian)
    else:
        e_entry = _u32(head, 24, endian)
        e_phoff = _u32(head, 28, endian)
        e_shoff = _u32(head, 32, endian)
        e_phentsize = _u16(head, 42, endian)
        e_phnum = _u16(head, 44, endian)
        e_shentsize = _u16(head, 46, endian)
        e_shnum = _u16(head, 48, endian)
        e_shstrndx = _u16(head, 50, endian)
    machines = {3: "x86", 8: "MIPS", 20: "PowerPC", 21: "PowerPC64", 40: "ARM",
                62: "x86-64", 183: "AArch64", 243: "RISC-V"}
    types = {1: "relocatable", 2: "executable", 3: "shared object", 4: "core"}
    details = {
        "class": "ELF64" if is64 else "ELF32",
        "endian": "little" if ei_data == 1 else "big",
        "type": types.get(e_type, hex(e_type)),
        "machine": machines.get(e_machine, hex(e_machine)),
        "entry": hex(e_entry),
        "program_headers": e_phnum,
        "section_headers": e_shnum,
    }
    if not e_shoff or not e_shnum:
        return {"format": "ELF", "details": details,
                "capabilities": ["inspect"], "function_diff": False,
                "note": "section table stripped or unavailable"}
    # Read section headers and names.
    data = path.read_bytes()
    sections = []
    names = b""
    shstr = None
    if e_shstrndx < e_shnum:
        off = e_shoff + e_shstrndx * e_shentsize
        shstr_off = _u64(data, off + 24, endian) if is64 else _u32(data, off + 16, endian)
        shstr_size = _u64(data, off + 32, endian) if is64 else _u32(data, off + 20, endian)
        names = data[shstr_off:shstr_off + shstr_size]
    for i in range(min(e_shnum, 80)):
        off = e_shoff + i * e_shentsize
        if off + (64 if is64 else 40) > len(data):
            break
        if is64:
            name_off = _u32(data, off, endian)
            sh_type = _u32(data, off + 4, endian)
            sh_size = _u64(data, off + 32, endian)
        else:
            name_off = _u32(data, off, endian)
            sh_type = _u32(data, off + 4, endian)
            sh_size = _u32(data, off + 20, endian)
        name = _cstr(names, name_off) if names and name_off < len(names) else ""
        sections.append({"name": name, "type": sh_type, "size": sh_size})
    details["sections"] = [s["name"] for s in sections if s["name"]][:30]
    details["has_symtab"] = any(s["name"] == ".symtab" for s in sections)
    details["has_dynsym"] = any(s["name"] == ".dynsym" for s in sections)
    details["has_debug_info"] = any(s["name"].startswith(".debug_info") for s in sections)
    details["has_build_id"] = ".note.gnu.build-id" in [s["name"] for s in sections]
    return {"format": "ELF", "details": details,
            "capabilities": ["inspect", "disassemble"] + (["ppc_diff"] if e_machine == 20 else []),
            "function_diff": e_machine == 20,
            "note": "PowerPC ELF can use PPC Diff with a Ghidra CSV; other ELF machines are inspect-only"}


def _macho(path: Path, head: bytes):
    magic = _u32(head, 0, ">")
    if magic in (0xCAFEBABE, 0xCAFEBABF):
        n = _u32(head, 4, ">")
        arches = []
        for i in range(min(n, 8)):
            off = 8 + i * 20
            if off + 20 > len(head):
                break
            cpu = _u32(head, off, ">")
            arches.append(hex(cpu))
        return {"format": "Mach-O universal", "details": {"architectures": arches},
                "capabilities": ["inspect"], "function_diff": False,
                "note": "fat Mach-O; select a slice for deeper analysis"}
    little = magic in (0xCEFAEDFE, 0xCFFAEDFE)
    endian = "<" if little else ">"
    if magic not in (0xFEEDFACE, 0xFEEDFACF, 0xCEFAEDFE, 0xCFFAEDFE):
        return {"format": "Mach-O", "error": "unknown magic"}
    is64 = magic in (0xFEEDFACF, 0xCFFAEDFE)
    cputype = _u32(head, 4, endian)
    ncmds = _u32(head, 16, endian)
    sizeofcmds = _u32(head, 20, endian)
    cpus = {7: "x86", 0x01000007: "x86-64", 12: "ARM", 0x0100000C: "ARM64"}
    details = {"class": "Mach-O 64" if is64 else "Mach-O 32", "cpu": cpus.get(cputype, hex(cputype)),
               "load_commands": ncmds, "sizeofcmds": sizeofcmds}
    # Parse load commands from the file header.
    data = path.read_bytes()
    off = 32 if is64 else 28
    segments, nsyms, uuid = [], None, None
    for _ in range(min(ncmds, 64)):
        if off + 8 > len(data):
            break
        cmd = _u32(data, off, endian)
        cmdsize = _u32(data, off + 4, endian)
        if cmdsize < 8:
            break
        if cmd in (0x1, 0x19) and off + 24 <= len(data):
            # LC_SEGMENT / LC_SEGMENT_64
            name_off = off + 8 if cmd == 0x1 else off + 8
            segments.append(_cstr(data, name_off, 16))
        if cmd == 0x2:  # LC_SYMTAB
            nsyms = _u32(data, off + 12, endian)
        if cmd == 0x1B and off + 24 <= len(data):  # LC_UUID
            uuid = data[off + 8:off + 24].hex()
        off += cmdsize
    details["segments"] = [s for s in segments if s][:20]
    details["symbols"] = nsyms
    if uuid:
        details["uuid"] = uuid
    return {"format": "Mach-O", "details": details,
            "capabilities": ["inspect"], "function_diff": False,
            "note": "Mach-O inspection only; no diff adapter"}


def _zip_probe(path: Path):
    try:
        z = zipfile.ZipFile(path)
        names = z.namelist()
    except Exception as e:
        return {"format": "ZIP", "error": str(e), "capabilities": ["inspect"],
                "function_diff": False}
    lower = [n.lower() for n in names]
    dex = [n for n in names if n.lower().endswith(".dex")]
    so = [n for n in names if n.lower().endswith(".so")]
    classes = [n for n in names if n.lower().endswith(".class")]
    payload = [n for n in names if n.lower().startswith("payload/")]
    if dex:
        fmt = "Android APK"
        abis = sorted({n.split("/")[1] for n in so if n.startswith("lib/") and n.count("/") >= 2})
        details = {"entries": len(names), "dex_files": len(dex), "native_libs": len(so),
                   "abis": abis, "manifest": any(n.lower() == "androidmanifest.xml" for n in lower)}
        # LIEF gives a real class/method inventory when available.
        try:
            import lief
            classes = methods = 0
            packages = set()
            for name in dex[:8]:
                data = z.read(name)
                fd, tmp = tempfile.mkstemp(suffix=".dex")
                os.close(fd)
                try:
                    with open(tmp, "wb") as f:
                        f.write(data)
                    d = lief.DEX.parse(tmp)
                    classes += len(d.classes)
                    methods += len(d.methods)
                    for i, c in enumerate(d.classes):
                        if i >= 2000:
                            break
                        cn = str(c.fullname)
                        if "/" in cn:
                            packages.add(cn.split("/")[0])
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            details["dex_classes"] = classes
            details["dex_methods"] = methods
            details["packages_sample"] = sorted(packages)[:20]
        except Exception as e:
            details["dex_error"] = str(e)[:200]
        return {"format": fmt, "details": details, "capabilities": ["inspect", "container", "dex_inventory"],
                "function_diff": False,
                "note": "APK class/method inventory available; DEX function diff is not implemented"}
    if payload:
        app_entries = [n for n in names if n.lower().startswith("payload/") and ".app/" in n.lower()]
        details = {"entries": len(names), "payload_entries": len(payload), "app_entries": len(app_entries)}
        return {"format": "iOS IPA", "details": details, "capabilities": ["inspect", "container"],
                "function_diff": False,
                "note": "IPA is a ZIP; Mach-O parsing inside is not implemented"}
    if classes:
        return {"format": "Java JAR", "details": {"entries": len(names), "class_files": len(classes)},
                "capabilities": ["inspect", "container"], "function_diff": False,
                "note": "class-file method diff is not implemented"}
    return {"format": "ZIP archive", "details": {"entries": len(names)}, "capabilities": ["inspect", "container"],
            "function_diff": False}


def _wasm(path: Path, head: bytes):
    details = {"version": _u32(head, 4, "<")}
    data = path.read_bytes()
    off = 8
    sections = []
    while off + 1 <= len(data):
        sid = data[off]
        off += 1
        # LEB128 length
        shift = 0
        size = 0
        while off < len(data):
            b = data[off]; off += 1
            size |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        sections.append(sid)
        off += size
        if off > len(data):
            break
    details["sections"] = sections[:30]
    return {"format": "WebAssembly", "details": details, "capabilities": ["inspect"],
            "function_diff": False, "note": "WASM section inspection only"}


def probe_file(path: Path):
    p = Path(path)
    try:
        with p.open("rb") as f:
            head = f.read(4096)
    except Exception as e:
        return {"format": "unreadable", "error": str(e), "capabilities": [], "function_diff": False}
    if head.startswith(b"\x7fELF"):
        return _elf(p, head)
    if head[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                    b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return _macho(p, head)
    if head.startswith(b"\0asm"):
        return _wasm(p, head)
    if head.startswith(b"PK\x03\x04"):
        return _zip_probe(p)
    if head.startswith(b"MZ"):
        return {"format": "PE / Windows executable", "details": {},
                "capabilities": ["inspect", "disassemble", "pdb_diff"], "function_diff": True,
                "note": "PE/PDB Release Diff supported"}
    if head.startswith(b"\x1aE\xdf\xa3"):
        return {"format": "Matroska / WebM", "details": {}, "capabilities": ["inspect"],
                "function_diff": False}
    if head[:4] == b"\x00\x00\x01\xba" or head[:4] == b"\x00\x00\x01\xb3":
        return {"format": "MPEG program stream", "details": {}, "capabilities": ["inspect"],
                "function_diff": False}
    if head.startswith(b"%PDF"):
        return {"format": "PDF", "details": {}, "capabilities": ["inspect"], "function_diff": False}
    if head.startswith(b"\x89PNG"):
        return {"format": "PNG image", "details": {}, "capabilities": ["inspect"], "function_diff": False}
    if head.startswith(b"\xff\xd8\xff"):
        return {"format": "JPEG image", "details": {}, "capabilities": ["inspect"], "function_diff": False}
    return {"format": "unknown binary", "details": {"magic": head[:8].hex()},
            "capabilities": ["hash"], "function_diff": False}


if __name__ == "__main__":
    import json, sys
    for p in sys.argv[1:]:
        print(json.dumps({"path": p, **probe_file(Path(p))}, indent=2))
