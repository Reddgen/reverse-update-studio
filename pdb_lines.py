"""PDB source-line index via DbgHelp (wide SRCCODEINFO variant)."""
import ctypes, ctypes.wintypes as wt, os, bisect
import enum_pdb as E

MAX_PATH = 260
SYMOPT_LOAD_LINES = 0x10

class SRCCODEINFOW(ctypes.Structure):
    _fields_ = [
        ('SizeOfStruct', wt.DWORD),
        ('Key', ctypes.c_void_p),
        ('ModBase', ctypes.c_ulonglong),
        ('Obj', wt.WCHAR * (MAX_PATH + 1)),
        ('FileName', wt.WCHAR * (MAX_PATH + 1)),
        ('LineNumber', wt.DWORD),
        ('Address', ctypes.c_ulonglong),
    ]

LINES_CALLBACK = ctypes.WINFUNCTYPE(wt.BOOL, ctypes.POINTER(SRCCODEINFOW), ctypes.c_void_p)
SymEnumLinesW = E.dbghelp.SymEnumLinesW
SymEnumLinesW.argtypes = [wt.HANDLE, ctypes.c_ulonglong, wt.LPCWSTR, wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
SymEnumLinesW.restype = wt.BOOL

class LineIndex:
    def __init__(self, exe_path):
        self.exe = os.path.abspath(exe_path)
        self.h = wt.HANDLE(-1)
        if not E.SymInitializeW(self.h, os.path.dirname(self.exe), False):
            raise ctypes.WinError(ctypes.get_last_error())
        E.SymSetOptions(2 | 4 | SYMOPT_LOAD_LINES)
        self.base = E.SymLoadModuleExW(self.h, None, self.exe, None, 0, 0, None, 0)
        if not self.base:
            raise RuntimeError('SymLoadModuleExW failed: %s' % ctypes.FormatError(ctypes.get_last_error()))
        self.addrs = []
        self.entries = []

        @LINES_CALLBACK
        def cb(info, ctx):
            rec = info.contents
            rva = int(rec.Address) - self.base
            name = rec.FileName
            self.addrs.append(rva)
            self.entries.append((rva, name, int(rec.LineNumber)))
            return True

        self._cb = cb
        ok = SymEnumLinesW(self.h, self.base, None, None, ctypes.cast(cb, ctypes.c_void_p), None)
        if not ok:
            raise RuntimeError('SymEnumLinesW failed: %s' % ctypes.FormatError(ctypes.get_last_error()))
        self.addrs.sort()
        self.entries.sort(key=lambda x: x[0])

    def max_in(self, rva, size):
        i = bisect.bisect_left(self.addrs, rva)
        j = bisect.bisect_left(self.addrs, rva + size)
        if j > i:
            return self.addrs[j - 1]
        return None

    def source_at(self, rva, size):
        """Return the last source line inside a function, or None."""
        i = bisect.bisect_left(self.addrs, rva)
        j = bisect.bisect_left(self.addrs, rva + max(1, size))
        if j <= i:
            return None
        entry = self.entries[j - 1]
        if not entry[1]:
            return None
        return {"file": entry[1], "line": entry[2]}

    def close(self):
        if getattr(self, 'h', None):
            E.dbghelp.SymCleanup(self.h)
            self.h = None

if __name__ == '__main__':
    import sys, json
    d = os.path.dirname(os.path.abspath(__file__))
    for ver, tag in [('v0.5.5', 'v055'), ('v0.5.6', 'v056'), ('v0.5.7', 'v057')]:
        exe = os.path.join(d, 'extracted', ver, 'openrct2.exe')
        li = LineIndex(exe)
        funcs = json.load(open(os.path.join(d, 'reports', 'symbols_%s.json' % tag), encoding='utf-8'))['functions']
        # quick coverage summary
        covered = 0
        near_end = 0
        for f in funcs:
            m = li.max_in(f['rva'], f['size'])
            if m is not None:
                covered += 1
                if f['rva'] + f['size'] * 0.5 <= m < f['rva'] + f['size']:
                    near_end += 1
        print(ver, 'lines', len(li.addrs), 'functions', len(funcs), 'covered', covered, 'line_max_in_upper_half', near_end)
