"""Write JSON so a reader never sees a half-written file.

Why: the catalogue state was read while the collector was writing it, and the read failed
with "Expecting value: line 1 column 1" - the file existed but was empty at that instant.
`write_text` truncates first and fills afterwards, so there is a window where the file is
invalid. Any other process - a checker, a merge, a person with an editor - that looks in
that window gets a corrupt file and cannot tell it apart from real corruption.

Writing to a temporary file in the same directory and then renaming it is atomic on Windows
and POSIX: a reader sees either the old file or the new one, never a partial one.

Usage:
    from atomicjson import write_json, read_json
    write_json(path, data)
    data = read_json(path, default={})
"""

import json
import os
import tempfile
import time
from pathlib import Path


def write_json(path, data, indent=None):
    """Write data as JSON, atomically.

    The temporary file is created in the same directory as the target, because a rename
    across volumes is not atomic and tempfile's default directory is often on another one.

    On Windows `os.replace` fails with PermissionError when the destination is open by
    another process - a checker reading the catalogue while a collector writes it is enough
    to lose the write. That is a transient condition, so it is retried with a short pause
    rather than failing the run.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handle, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())

        # os.replace is atomic on Windows and POSIX, unlike os.rename on Windows when the
        # destination exists. A reader holding the file open makes it fail for a moment.
        last = None
        for attempt in range(8):
            try:
                os.replace(tmp_name, str(path))
                return
            except PermissionError as e:
                last = e
                time.sleep(0.25 * (attempt + 1))
        raise last
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json(path, default=None):
    """Read JSON, returning default when the file is missing.

    A missing file is normal on a first run. A file that exists but does not parse is not,
    and it is raised rather than swallowed - a silently-defaulted read is how a run
    quietly starts over and loses everything it had.
    """
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8", newline="") as f:
        return json.load(f)
