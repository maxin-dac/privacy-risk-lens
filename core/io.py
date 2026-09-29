import io as _io
import csv
import os
import math
from contextlib import contextmanager
import pandas as pd

@contextmanager
def _buffer(obj):
    """Fournit un flux lisible sans fermer les objets appartenant à l'appelant."""
    if isinstance(obj, (bytes, bytearray)):
        with _io.BytesIO(obj) as stream:
            yield stream
        return
    if hasattr(obj, "read"):
        try:
            position = obj.tell()
            obj.seek(0)
        except (AttributeError, OSError, ValueError) as exc:
            raise ValueError("file_not_seekable") from exc
        try:
            yield obj
        finally:
            obj.seek(position)
        return
    with open(obj, "rb") as stream:
        yield stream

def _enc_detect(raw):
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(raw).best()
        if best is not None:
            return best.encoding
    except Exception:
        pass
    return "utf-8"

def count_rows(obj, sep, enc):
    with _buffer(obj) as f:
        text = _io.TextIOWrapper(f, encoding=enc, errors="replace", newline="")
        try:
            reader = csv.reader(text, delimiter=sep)
            next(reader, None)
            return sum(1 for row in reader if row)
        finally:
            text.detach()

def sniff(obj):
    with _buffer(obj) as f:
        raw = f.read(64 * 1024)
    if not raw:
        raise ValueError("empty")
    enc = _enc_detect(raw)
    text = raw.decode(enc, errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]
        enc = "utf-8-sig" if enc.startswith("utf-8") else enc
    try:
        sep = csv.Sniffer().sniff(text, delimiters=",;\t|").delimiter
    except csv.Error:
        sep = ","
    head = pd.read_csv(_io.StringIO(text), sep=sep, encoding=enc, nrows=0)
    cols = list(head.columns)
    if not cols:
        raise ValueError("nocols")
    return enc, sep, cols

def load_sampled(obj, sep, enc, max_rows_full=None, sample_n=None):
    max_rows_full = int(os.getenv("PRL_MAX_ROWS_FULL", 300_000 if max_rows_full is None else max_rows_full))
    sample_n = int(os.getenv("PRL_SAMPLE_N", 200_000 if sample_n is None else sample_n))
    if max_rows_full < 1 or sample_n < 1:
        raise ValueError("invalid_limits")
    total = count_rows(obj, sep, enc)
    if total == 0:
        raise ValueError("empty")
    if total <= max_rows_full:
        with _buffer(obj) as f:
            df = pd.read_csv(f, sep=sep, encoding=enc)
        return df, total, False
    stride = max(1, math.ceil(total / sample_n))
    # echantillon systatique uniforme, memoire bornee (pandas ne garde que les lignes prises)
    with _buffer(obj) as f:
        df = pd.read_csv(f, sep=sep, encoding=enc,
                         skiprows=lambda i: i > 0 and ((i - 1) % stride) != 0)
    return df, total, True