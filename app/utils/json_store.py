"""Concurrency-safe JSON file storage.

Writers serialize on an flock'ed sidecar ``<name>.lock`` file (works across
threads and processes) and replace the target atomically via a temp file +
``os.replace``, so a concurrent reader can never observe a truncated file and
concurrent read-modify-write cycles cannot lose updates.
"""
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

_MISSING = object()


@contextmanager
def _locked(path: Path):
    lock_path = path.with_name(path.name + ".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _read(path: Path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        if default is _MISSING:
            raise
        return default


def _replace_with(path: Path, serialized: str):
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(serialized)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_json(path, default=_MISSING):
    """Read a JSON file; returns ``default`` if the file does not exist.

    Needs no lock: writers replace the file atomically, so a read always
    sees a complete document.
    """
    return _read(Path(path), default)


def write_json(path, data):
    """Atomically create or overwrite a JSON file."""
    path = Path(path)
    with _locked(path):
        _replace_with(path, json.dumps(data))


class _Ref:
    __slots__ = ("data",)

    def __init__(self, data):
        self.data = data


@contextmanager
def edit_json(path, default=_MISSING):
    """Locked read-modify-write cycle.

    Yields a ref whose ``data`` holds the parsed file (or ``default`` if the
    file does not exist). Mutate it in place or reassign ``ref.data``; on
    clean exit the result is written back atomically, but only if it changed.
    An exception inside the block skips the write.
    """
    path = Path(path)
    with _locked(path):
        data = _read(path, default)
        before = json.dumps(data)
        ref = _Ref(data)
        yield ref
        after = json.dumps(ref.data)
        if after != before:
            _replace_with(path, after)
