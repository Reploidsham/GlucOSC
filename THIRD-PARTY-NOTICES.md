# Third-party notices

GlucOSC's own code is MIT-licensed (see `LICENSE`). The Windows and Linux downloads also bundle these
open-source components. Their full license texts are in the `licenses` folder next to the program
(Windows: `GlucOSC\licenses`; Linux: inside the AppImage under `usr/lib/GlucOSC/licenses`,
which `./GlucOSC-x86_64.AppImage --appimage-extract` unpacks).

| Component | License | Source |
|---|---|---|
| Qt 6 and Qt for Python (PySide6, Shiboken6) | LGPL-3.0 (also available under GPL / commercial terms) | <https://code.qt.io/cgit/pyside/pyside-setup.git/>, <https://download.qt.io/official_releases/qt/> |
| Python | Python Software Foundation License | <https://www.python.org/downloads/source/> |
| PyInstaller bootloader | GPL-2.0 with a special exception that allows bundling | <https://github.com/pyinstaller/pyinstaller> |

**About the LGPL (Qt / PySide6):** the apps use Qt as separate shared library files (the download is a
folder, not a single exe), so you can replace them with your own build of the same Qt version. The exact
PySide6 version is listed in `packaging/requirements-build.txt` in the source repository.

The Unity package contains only GlucOSC's own files (MIT).
