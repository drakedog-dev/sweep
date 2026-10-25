"""Write version_info.txt for PyInstaller (--version-file) from APP_VERSION in sweep/platform.py.
Product name and version end up in Sweep.exe properties, which code signing services and antivirus software look at."""
import re
import sys
from pathlib import Path

app = Path(__file__).resolve().parents[1]
ver = re.search(r'APP_VERSION = "([\d.]+)"', (app / "sweep" / "platform.py").read_text("utf-8")).group(1)
nums = [int(x) for x in ver.split(".")] + [0, 0, 0, 0]
t = tuple(nums[:4])
text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Sweep'),
      StringStruct('FileDescription', 'Sweep: Windows cleaner and optimiser'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('InternalName', 'Sweep'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Alex (Drakedog). MIT License.'),
      StringStruct('OriginalFilename', 'Sweep.exe'),
      StringStruct('ProductName', 'Sweep'),
      StringStruct('ProductVersion', '{ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
out = Path(sys.argv[1]) if len(sys.argv) > 1 else app / "version_info.txt"
out.write_text(text, "utf-8")
print(f"version file for {ver}: {out}")
