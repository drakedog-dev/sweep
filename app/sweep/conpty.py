"""Run a console program inside a Windows pseudo console (ConPTY, Windows 10 1809 and later).

Console programs such as winget hold back their progress bar when their output goes to a pipe and print it
only at the end. Inside a pseudo console they believe a terminal is attached and draw the bar live, which is
what Sweep needs to show a real download progress. No window is shown and no extra files are shipped:
everything here is plain kernel32."""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

from . import platform as P

EXTENDED_STARTUPINFO_PRESENT = 0x00080000
STARTF_USESTDHANDLES = 0x00000100
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
WAIT_TIMEOUT = 0x102


class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


def _k32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p, wintypes.DWORD]
    k.CreatePipe.restype = wintypes.BOOL
    k.CreatePseudoConsole.argtypes = [COORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    k.CreatePseudoConsole.restype = ctypes.c_long
    k.ClosePseudoConsole.argtypes = [wintypes.HANDLE]
    k.ClosePseudoConsole.restype = None
    k.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
    k.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    k.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    k.UpdateProcThreadAttribute.restype = wintypes.BOOL
    k.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    k.DeleteProcThreadAttributeList.restype = None
    k.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFOEXW), ctypes.POINTER(PROCESS_INFORMATION)]
    k.CreateProcessW.restype = wintypes.BOOL
    k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.ReadFile.restype = wintypes.BOOL
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.GetExitCodeProcess.restype = wintypes.BOOL
    k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k.TerminateProcess.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    return k


def available() -> bool:
    if not P.IS_WINDOWS:
        return False
    try:
        return hasattr(ctypes.WinDLL("kernel32"), "CreatePseudoConsole")
    except OSError:
        return False


def run(cmdline: str, on_text, timeout: float, cols: int = 160, rows: int = 40) -> int | None:
    """Start cmdline in a hidden pseudo console and pass its output to on_text(str) as it arrives.
    Returns the exit code, -2 after a timeout, or None when ConPTY cannot be used (the caller falls back to a pipe)."""
    if not available():
        return None
    k = _k32()
    in_read, in_write, out_read, out_write = wintypes.HANDLE(), wintypes.HANDLE(), wintypes.HANDLE(), wintypes.HANDLE()
    if not k.CreatePipe(ctypes.byref(in_read), ctypes.byref(in_write), None, 0):
        return None
    if not k.CreatePipe(ctypes.byref(out_read), ctypes.byref(out_write), None, 0):
        k.CloseHandle(in_read)
        k.CloseHandle(in_write)
        return None
    hpc = wintypes.HANDLE()
    hr = k.CreatePseudoConsole(COORD(cols, rows), in_read, out_write, 0, ctypes.byref(hpc))
    k.CloseHandle(in_read)          # the pseudo console holds its own copies now
    k.CloseHandle(out_write)
    if hr != 0:
        P.log(f"conpty: CreatePseudoConsole failed {hr & 0xFFFFFFFF:#x}")
        k.CloseHandle(in_write)
        k.CloseHandle(out_read)
        return None

    size = ctypes.c_size_t(0)
    k.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
    attrs = (ctypes.c_byte * size.value)()
    si = STARTUPINFOEXW()
    si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
    # no inherited standard handles: the child must talk to the pseudo console, not to Sweep's own (possibly redirected) ones
    si.StartupInfo.dwFlags = STARTF_USESTDHANDLES
    pi = PROCESS_INFORMATION()
    ok = (k.InitializeProcThreadAttributeList(attrs, 1, 0, ctypes.byref(size))
          and k.UpdateProcThreadAttribute(attrs, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE, hpc.value, ctypes.sizeof(wintypes.HANDLE), None, None))
    if ok:
        si.lpAttributeList = ctypes.cast(attrs, ctypes.c_void_p)
        buf = ctypes.create_unicode_buffer(cmdline)
        ok = k.CreateProcessW(None, buf, None, None, False, EXTENDED_STARTUPINFO_PRESENT, None, None, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        P.log(f"conpty: could not start the process (error {ctypes.get_last_error()})")
        k.ClosePseudoConsole(hpc)
        k.CloseHandle(in_write)
        k.CloseHandle(out_read)
        k.DeleteProcThreadAttributeList(attrs)
        return None

    def reader():
        import codecs
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        chunk = ctypes.create_string_buffer(8192)
        n = wintypes.DWORD(0)
        while k.ReadFile(out_read, chunk, len(chunk), ctypes.byref(n), None) and n.value:
            try:
                on_text(dec.decode(chunk.raw[:n.value]))
            except Exception:  # noqa: BLE001
                pass

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    t0 = time.time()
    code = wintypes.DWORD(0)
    timed_out = False
    while k.WaitForSingleObject(pi.hProcess, 250) == WAIT_TIMEOUT:
        if time.time() - t0 > timeout:
            k.TerminateProcess(pi.hProcess, 1)
            timed_out = True
            break
    k.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    time.sleep(0.2)                  # let the last frame through
    k.ClosePseudoConsole(hpc)        # ends the output stream, the reader stops
    th.join(5)
    for h in (pi.hThread, pi.hProcess, in_write, out_read):
        k.CloseHandle(h)
    k.DeleteProcThreadAttributeList(attrs)
    return -2 if timed_out else int(code.value)
