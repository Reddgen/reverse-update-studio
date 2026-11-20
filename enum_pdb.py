"""Enumerate function symbols from a PE + PDB using Windows DbgHelp.

No execution of the target: DbgHelp only maps the image and parses debug data.
"""
import ctypes, ctypes.wintypes as wt, json, sys, os, time

dbghelp = ctypes.WinDLL('dbghelp', use_last_error=True)

MAX_SYM_NAME = 2000

class SYMBOL_INFOW(ctypes.Structure):
    _fields_ = [
        ('SizeOfStruct', wt.DWORD),
        ('TypeIndex', wt.DWORD),
        ('Reserved', ctypes.c_ulonglong * 2),
        ('Index', wt.DWORD),
        ('Size', wt.DWORD),
        ('ModBase', ctypes.c_ulonglong),
        ('Flags', wt.DWORD),
        ('Value', ctypes.c_ulonglong),
        ('Address', ctypes.c_ulonglong),
        ('Register', wt.DWORD),
        ('Scope', wt.DWORD),
        ('Tag', wt.DWORD),
        ('NameLen', wt.DWORD),
        ('MaxNameLen', wt.DWORD),
        ('Name', ctypes.c_wchar * 1),
    ]

class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ('BaseOfDll', ctypes.c_ulonglong),
        ('SizeOfImage', wt.DWORD),
        ('EntryPoint', ctypes.c_ulonglong),
    ]

class IMAGEHLP_MODULEW64(ctypes.Structure):
    _fields_ = [
        ('SizeOfStruct', wt.DWORD),
        ('BaseOfImage', ctypes.c_ulonglong),
        ('ImageSize', wt.DWORD),
        ('TimeDateStamp', wt.DWORD),
        ('CheckSum', wt.DWORD),
        ('NumSyms', wt.DWORD),
        ('SymType', wt.DWORD),
        ('ModuleName', wt.WCHAR * 32),
        ('ImageName', wt.WCHAR * 256),
        ('LoadedImageName', wt.WCHAR * 256),
        ('LoadedPdbName', wt.WCHAR * 256),
        ('CVSig', wt.DWORD),
        ('CVData', wt.WCHAR * 780),
        ('PdbSig', wt.DWORD),
        ('PdbSig70', ctypes.c_ubyte * 16),
        ('PdbAge', wt.DWORD),
        ('PdbUnmatched', wt.BOOL),
        ('DbgUnmatched', wt.BOOL),
        ('LineNumbers', wt.BOOL),
        ('GlobalSymbols', wt.BOOL),
        ('TypeInfo', wt.BOOL),
        ('SourceIndexed', wt.BOOL),
        ('Publics', wt.BOOL),
        ('MachineType', wt.DWORD),
        ('Reserved', wt.DWORD),
        ('Reserved2', wt.DWORD),
        ('Reserved3', wt.DWORD),
    ]

SymInitializeW = dbghelp.SymInitializeW
SymInitializeW.argtypes = [wt.HANDLE, wt.LPCWSTR, wt.BOOL]
SymInitializeW.restype = wt.BOOL
SymSetOptions = dbghelp.SymSetOptions
SymSetOptions.argtypes = [wt.DWORD]
SymSetOptions.restype = wt.DWORD
SymLoadModuleExW = dbghelp.SymLoadModuleExW
SymLoadModuleExW.argtypes = [wt.HANDLE, wt.HANDLE, wt.LPCWSTR, wt.LPCWSTR, ctypes.c_ulonglong, wt.DWORD, ctypes.c_void_p, wt.DWORD]
SymLoadModuleExW.restype = ctypes.c_ulonglong
SymEnumSymbolsW = dbghelp.SymEnumSymbolsW
SymEnumSymbolsW.argtypes = [wt.HANDLE, ctypes.c_ulonglong, wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
SymEnumSymbolsW.restype = wt.BOOL
SymGetModuleInfoW64 = dbghelp.SymGetModuleInfoW64
SymGetModuleInfoW64.argtypes = [wt.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(IMAGEHLP_MODULEW64)]
SymGetModuleInfoW64.restype = wt.BOOL

SYMOPT_UNDNAME = 0x00000002
SYMOPT_DEFERRED_LOADS = 0x00000004

CALLBACK = ctypes.WINFUNCTYPE(wt.BOOL, ctypes.POINTER(SYMBOL_INFOW), wt.ULONG, ctypes.c_void_p)

def enumerate_functions(exe_path, symbol_path=None):
    hproc = wt.HANDLE(-1)  # GetCurrentProcess pseudo handle
    if not SymInitializeW(hproc, symbol_path, False):
        raise ctypes.WinError(ctypes.get_last_error())
    SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS)
    base = SymLoadModuleExW(hproc, None, os.path.abspath(exe_path), None, 0, 0, None, 0)
    if not base:
        err = ctypes.get_last_error()
        raise RuntimeError(f'SymLoadModuleExW failed for {exe_path}: {err} {ctypes.FormatError(err)}')
    mi = IMAGEHLP_MODULEW64()
    mi.SizeOfStruct = ctypes.sizeof(IMAGEHLP_MODULEW64)
    ok = SymGetModuleInfoW64(hproc, base, ctypes.byref(mi))
    funcs = []

    @CALLBACK
    def cb(sym, symbol_size, ctx):
        try:
            if sym.contents.Tag == 5:  # SymTagFunction
                name = ctypes.wstring_at(ctypes.addressof(sym.contents) + SYMBOL_INFOW.Name.offset, sym.contents.NameLen)
                funcs.append({
                    'name': name,
                    'address': int(sym.contents.Address),
                    'rva': int(sym.contents.Address - base),
                    'size': int(sym.contents.Size),
                    'tag': int(sym.contents.Tag),
                    'flags': int(sym.contents.Flags),
                })
        except Exception:
            pass
        return True

    t0 = time.time()
    ok2 = SymEnumSymbolsW(hproc, base, None, ctypes.cast(cb, ctypes.c_void_p), None)
    err = ctypes.get_last_error()
    meta = {
        'exe': os.path.abspath(exe_path),
        'base': base,
        'module_info_ok': bool(ok),
        'sym_type': mi.SymType if ok else None,
        'module_name': mi.ModuleName if ok else None,
        'image_name': mi.ImageName if ok else None,
        'loaded_image_name': mi.LoadedImageName if ok else None,
        'loaded_pdb_name': mi.LoadedPdbName if ok else None,
        'pdb_unmatched': bool(mi.PdbUnmatched) if ok else None,
        'publics': bool(mi.Publics) if ok else None,
        'global_symbols': bool(mi.GlobalSymbols) if ok else None,
        'type_info': bool(mi.TypeInfo) if ok else None,
        'num_syms': mi.NumSyms if ok else None,
        'enum_ok': bool(ok2),
        'enum_error': err if not ok2 else 0,
        'function_count': len(funcs),
        'elapsed_s': round(time.time() - t0, 2),
    }
    return funcs, meta

if __name__ == '__main__':
    exe = sys.argv[1]
    out = sys.argv[2]
    sympath = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(os.path.abspath(exe))
    funcs, meta = enumerate_functions(exe, sympath)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'functions': funcs}, f)
    print(json.dumps(meta, indent=2))
