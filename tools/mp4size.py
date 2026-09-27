"""Read a video's pixel size out of the MP4 header without ffprobe.

Why this exists: the download endpoints on moewalls and wallpaperwaifu serve files written
without faststart, so the `moov` atom sits at the end. Fetching only the head returns no
dimensions, and fetching only the tail does not help either - the box offsets inside `moov`
point into a file that is not there, so ffprobe reports "moov atom not found" even though
`moov` and `tkhd` are plainly present in the bytes.

The size is in the `tkhd` box, at a fixed offset, as two 16.16 fixed-point numbers. Reading
them directly needs no external tool and no whole-file download.

Run: python -c "from mp4size import size_from_bytes; print(size_from_bytes(open('f.mp4','rb').read()))"
"""

import struct


def _find_box(data, name, start=0):
    """The offset of a box by its four-character name, or -1."""
    return data.find(name, start)


def size_from_bytes(data):
    """(width, height) from the first `tkhd` box in data, or None.

    `tkhd` layout, counted from the box's size field:
        size(4) type(4) version(1) flags(3)
        version 0: creation(4) modified(4) trackid(4) reserved(4) duration(4)
        version 1: creation(8) modified(8) trackid(4) reserved(4) duration(8)
        then reserved(8) layer(2) altgroup(2) volume(2) reserved(2) matrix(36)
        then width(4) height(4) as 16.16 fixed point

    The version byte is at offset 0 of the `version + flags` word. An earlier version of
    this read the whole word and compared it to 1, which matched only when the flags were
    also 1 - so most files took the version-1 branch and the dimensions came out as 16384
    (the value of an all-but-one-bit set word) by the height of the real video.

    A width or height that is exactly 16384 is the giveaway for that fault: it is the
    largest value a 16.16 word can hold below the sign bit, and it appears when the parser
    reads one word too early.
    """
    i = _find_box(data, b"tkhd")
    if i < 0:
        return None

    box = data[i + 4:]              # skip the name, land on version + flags
    if len(box) < 92:
        return None

    version = box[0]                # the byte itself, not the word
    base = 88 if version == 1 else 76

    if len(box) < base + 8:
        return None

    try:
        width = struct.unpack(">I", box[base:base + 4])[0] / 65536.0
        height = struct.unpack(">I", box[base + 4:base + 8])[0] / 65536.0
    except struct.error:
        return None

    if not (16 <= width <= 16384 and 16 <= height <= 16384):
        return None
    # 16384 exactly means the read landed on the wrong word.
    if width == 16384 or height == 16384:
        return None
    return int(round(width)), int(round(height))


def size_from_sample_entry(data):
    """(width, height) from an avc1/hvc1/vp09/av01 sample description, or None.

    A fallback for files whose `tkhd` is damaged. These boxes carry the size as two
    big-endian 16-bit integers at a fixed offset from the box name.
    """
    for tag in (b"avc1", b"hvc1", b"hev1", b"vp09", b"av01", b"mp4v"):
        i = _find_box(data, tag)
        if i < 0:
            continue
        # size(4) name(4) reserved(6) dataref(2) pre_defined(2) reserved(2)
        # pre_defined(12) width(2) height(2)
        j = i + 4 + 6 + 2 + 2 + 2 + 12
        if len(data) < j + 4:
            continue
        try:
            width = struct.unpack(">H", data[j:j + 2])[0]
            height = struct.unpack(">H", data[j + 2:j + 4])[0]
        except struct.error:
            continue
        if 16 <= width <= 16384 and 16 <= height <= 16384:
            return width, height
    return None


def size_from_file(path):
    """Read the first and last megabyte of a file and return its video size."""
    with open(path, "rb") as f:
        head = f.read(1_500_000)
        found = size_from_bytes(head) or size_from_sample_entry(head)
        if found:
            return found
        try:
            f.seek(0, 2)
            total = f.tell()
            if total > 1_500_000:
                f.seek(max(0, total - 1_500_000))
                tail = f.read()
                return size_from_bytes(tail) or size_from_sample_entry(tail)
        except OSError:
            pass
    return None
