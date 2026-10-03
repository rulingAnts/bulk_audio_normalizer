# License texts kept in the repository

`collect_licenses.py` puts the license of everything the app bundles into the app's
`licenses` folder. Most come from the installed packages themselves; these files cover the
parts that ship none:

- `python-incorporated-software.txt`: the "Licenses and Acknowledgements for Incorporated
  Software" section of CPython 3.11's `Doc/license.rst` (OpenSSL, expat, libffi, zlib,
  libmpdec, ...). Python's own `LICENSE.txt` does not include it.
- `ncurses.txt`: ncurses' `COPYING` (the python.org macOS Python bundles libncursesw).
- `pyobjc.txt`: PyObjC's MIT license; several pyobjc-framework-* wheels ship no copy.
- `proxy_tools.txt`: proxy_tools' `LICENSE.txt` (BSD); its wheel ships none.
- `pythonnet.txt`, `clr_loader.txt`: their `LICENSE` files (MIT); on Windows pywebview uses
  them, and their wheels ship none.

If a new dependency ships no license file, `collect_licenses.py` stops the build: add its
text here and its name to `STATIC_FOR` in `collect_licenses.py`.
