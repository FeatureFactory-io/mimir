"""Read-only bounded RGB/RGBA PNG proof; no mutable image/runtime dependency."""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

_MAX_FILE = 8 * 1024**2
_MAX_CHUNKS = 4096
_COMPRESSED_BLOCK = 8192
_MAX_PIXELS = 16 * 1024**2
_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class Png(NamedTuple):
    """Validated finite actual Chromium screenshot scanline declaration."""

    width: int
    height: int
    channels: int
    encoded: tuple[memoryview, ...]


def png_nonuniform(path: Path) -> bool:
    """Read actual PNG pixels and reject a uniform acquisition.

    :param path: Existing owned original Chromium RGB/RGBA PNG.
    :return: True for at least two distinct actual pixels; False for one color.
    :raises ValueError: Unsupported, corrupt or oversized acquisition.
    """
    if (
        path.is_symlink()
        or not path.is_file()
        or not 0 < path.stat().st_size <= _MAX_FILE
    ):
        raise ValueError("Bounded actual regular PNG acquisition required.")
    return png_bytes_nonuniform(path.read_bytes())


def png_bytes_nonuniform(raw: bytes) -> bool:
    """Validate actual bounded RGB/RGBA PNG bytes and detect visible pixel variation.

    :param raw: Actual original bytes or one downloaded archive PNG member.
    :return: Whether pixels vary; this is not an independent UI visual verdict.
    :raises ValueError: Invalid, corrupt, oversized or unsupported PNG.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_FILE:
        raise ValueError("Bounded actual PNG bytes required.")
    png = _decode(raw)
    stride = png.width * png.channels
    previous, first, nonuniform = bytes(stride), None, False
    inflater = _Inflater(stride + 1, png.height)
    for scanline in _scanlines(png.encoded, inflater):
        if scanline[0] not in {0, 1, 2, 3, 4}:
            raise ValueError("Actual standard PNG scanline filter required.")
        if nonuniform:
            continue
        row = _unfilter(scanline[0], scanline[1:], previous, png.channels)
        first = row[: png.channels] if first is None else first
        nonuniform = row != first * png.width
        previous = row
    return nonuniform


def _decode(raw: bytes) -> Png:
    """Validate bounded PNG chunks, exact pixel layout and finite zlib payload.

    :param raw: Exact acquired PNG bytes.
    :return: Decoded supported scanline data.
    :raises ValueError: Signature, CRC, dimensions, compression or layout differs.
    """
    chunks = _chunks(raw)
    width, height, depth, kind, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1]
    )
    if (
        depth != 8
        or kind not in {2, 6}
        or compression
        or filtering
        or interlace
        or not 0 < width * height <= _MAX_PIXELS
    ):
        raise ValueError("Bounded native8-bit RGB/RGBA noninterlaced PNG required.")
    channels = 3 if kind == 2 else 4
    if width > 8192 or height > 32768:
        raise ValueError("Native PNG row/document dimensions exceed bounds.")
    encoded = tuple(data for name, data in chunks if name == b"IDAT")
    return Png(width, height, channels, encoded)


def _chunks(raw: bytes) -> list[tuple[bytes, memoryview]]:
    """Read actual CRC-checked PNG chunks without accepting trailing aliases/data.

    :param raw: Actual bounded file bytes.
    :return: Exact supported chunk sequence, beginning IHDR and ending IEND.
    :raises ValueError: Chunk size, order, CRC or termination differs.
    """
    if not raw.startswith(_SIGNATURE):
        raise ValueError("Actual PNG signature required.")
    offset, chunks = len(_SIGNATURE), []
    view = memoryview(raw)
    while offset + 12 <= len(raw):
        size = struct.unpack(">I", raw[offset : offset + 4])[0]
        name, end = raw[offset + 4 : offset + 8], offset + 12 + size
        if end > len(raw):
            raise ValueError("Actual PNG chunk is truncated.")
        data = view[offset + 8 : end - 4]
        if (
            zlib.crc32(data, zlib.crc32(name)) & 0xFFFFFFFF
            != struct.unpack(">I", raw[end - 4 : end])[0]
        ):
            raise ValueError("Actual PNG chunk CRC differs.")
        if len(chunks) >= _MAX_CHUNKS:
            raise ValueError("Actual PNG chunk count exceeds its bound.")
        chunks.append((name, data))
        offset = end
        if name == b"IEND":
            break
    _complete_chunks(chunks, offset, len(raw))
    return chunks


def _complete_chunks(
    chunks: list[tuple[bytes, memoryview]], offset: int, total: int
) -> None:
    """Require exactly one header and complete bounded PNG pixel termination.

    :param chunks: Actual CRC-checked chunks.
    :param offset: Actual parsed end position.
    :param total: Actual file byte length.
    :return: None after header/pixels/end topology validates.
    :raises ValueError: Missing, duplicate or trailing critical structures.
    """
    if (
        not chunks
        or chunks[0][0] != b"IHDR"
        or len(chunks[0][1]) != 13
        or chunks[-1] != (b"IEND", b"")
        or offset != total
        or not any(name == b"IDAT" for name, _ in chunks)
    ):
        raise ValueError("Actual complete PNG header/pixels/end required.")

    if sum(name == b"IHDR" for name, _ in chunks) != 1:
        raise ValueError("Exactly one PNG header required.")


def _scanlines(encoded: tuple[memoryview, ...], inflater: _Inflater) -> Iterator[bytes]:
    """Inflate original pixels in8KiBinput chunks and one bounded scanline.

    :param encoded: Actual CRC-checked IDAT views, without copied compressed buffers.
    :param inflater: Exclusive finite row decoder.
    :return: Iterator over actual filtered row bytes.
    :raises ValueError: Corruption, excess rows or incomplete payload.
    """
    try:
        for data in encoded:
            for start in range(0, len(data), _COMPRESSED_BLOCK):
                yield from inflater.feed(data[start : start + _COMPRESSED_BLOCK])
        yield from inflater.feed(b"")
    except zlib.error as error:
        raise ValueError("Actual PNG compressed pixels are corrupt.") from error
    if (
        not inflater.decoder.eof
        or inflater.buffer
        or inflater.rows != inflater.expected
    ):
        raise ValueError("Actual PNG finite row layout differs.")


class _Inflater:
    """Own only one actual scanline and a bounded zlib input tail."""

    def __init__(self, row_size: int, expected: int) -> None:
        """Allocate exclusive finite row state.

        :param row_size: Validated one-row byte budget, including filter byte.
        :param expected: Validated finite expected row count.
        :return: None after bounded state allocation.
        """
        self.row_size, self.expected, self.rows = row_size, expected, 0
        self.buffer = bytearray()
        self.decoder = zlib.decompressobj()

    def feed(self, block: memoryview | bytes) -> Iterator[bytes]:
        """Inflate one bounded original block without retaining decoded pictures.

        :param block: At most8KiBactual compressed data or empty flush probe.
        :return: Exact bounded completed rows.
        :raises ValueError: Trailing compressed data or excess pixels.
        """
        pending = block
        while True:
            wanted = self.row_size - len(self.buffer)
            decoded = self.decoder.decompress(pending, wanted)
            pending = self.decoder.unconsumed_tail
            if self.decoder.unused_data:
                raise ValueError("Trailing PNG compressed data rejected.")
            self.buffer.extend(decoded)
            if len(self.buffer) == self.row_size:
                self.rows += 1
                if self.rows > self.expected:
                    raise ValueError("Actual PNG exceeds finite row count.")
                yield bytes(self.buffer)
                self.buffer.clear()
            if not pending and len(decoded) < wanted:
                break


def _unfilter(kind: int, raw: bytes, previous: bytes, channels: int) -> bytes:
    """Reverse standard PNG filters while preserving actual pixels.

    Reference: https://www.w3.org/TR/PNG-Filters.html (short specification).
    :param kind: Actual per-scanline PNG filter0–4.
    :param raw: Actual filtered RGB/RGBA bytes.
    :param previous: Previous completely reconstructed scanline.
    :param channels: Actual3or4byte pixel width.
    :return: Exact reconstructed scanline; source file is never edited.
    :raises ValueError: Unsupported filter kind.
    """
    if kind not in {0, 1, 2, 3, 4}:
        raise ValueError("Actual standard PNG scanline filter required.")
    row = bytearray(raw)
    for index, value in enumerate(raw):
        left = row[index - channels] if index >= channels else 0
        upper_left = previous[index - channels] if index >= channels else 0
        row[index] = (
            value + _prediction(kind, left, previous[index], upper_left)
        ) % 256
    return bytes(row)


def _prediction(kind: int, left: int, above: int, upper_left: int) -> int:
    """Apply exact PNG None/Sub/Up/Average/Paeth predictor arithmetic.

    :param kind: Validated filter kind.
    :param left: Reconstructed left byte or zero.
    :param above: Reconstructed previous-row byte or zero.
    :param upper_left: Reconstructed upper-left byte or zero.
    :return: Exact standard prediction with prescribed Paeth tie order.
    """
    if kind == 0:
        return 0
    if kind == 1:
        return left
    if kind == 2:
        return above
    if kind == 3:
        return (left + above) // 2
    estimate = left + above - upper_left
    distances = (
        abs(estimate - left),
        abs(estimate - above),
        abs(estimate - upper_left),
    )
    return (left, above, upper_left)[distances.index(min(distances))]
