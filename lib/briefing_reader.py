"""D-Day's eight interleaved Allied/Axis briefing lines in the Scenario block."""
import struct


BRIEFING_START = 4 + 0x3e0
BRIEFING_LINES = 8
LINE_BYTES = 128
SIDES = ('Allied', 'Axis')
# The supplied UTAH briefing stores the ü in Führer as 0x9f (Mac Roman).
ENCODING = 'mac_roman'


def _line_offset(side, line):
    return BRIEFING_START + (line * 2 + side) * LINE_BYTES


def _validate_header(data):
    if len(data) < 0x1234 or struct.unpack_from('<I', data)[0] != 0x1230:
        raise ValueError('Missing or unsupported D-Day Scenario block')


def read_briefings(data):
    """Read fixed slots, retaining short lines, blank lines, and side ownership."""
    _validate_header(data)
    texts = []
    for side in range(2):
        lines = []
        for line in range(BRIEFING_LINES):
            offset = _line_offset(side, line)
            lines.append(data[offset:offset + LINE_BYTES].split(b'\0', 1)[0].decode(ENCODING))
        # Unused trailing slots are not paragraphs. Keep spaces and internal blanks.
        texts.append('\n'.join(lines).rstrip('\n'))
    return tuple(texts)


def prepare_briefing_changes(data, texts):
    """Validate both sides before returning bounded (offset, bytes, side) patches.

    Only changed slots are rewritten; untouched padding and adjacent header
    fields survive exactly. There is no automatic truncation or line wrapping.
    """
    _validate_header(data)
    if len(texts) != 2:
        raise ValueError('Both Allied and Axis briefings are required')
    original = read_briefings(data)
    patches = []
    for side, text in enumerate(texts):
        if text == original[side]:
            continue
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        if len(lines) > BRIEFING_LINES:
            raise ValueError(f'{SIDES[side]} briefing has {len(lines)} lines; the game allows 8.')
        lines += [''] * (BRIEFING_LINES - len(lines))
        for line, value in enumerate(lines):
            try:
                encoded = value.encode(ENCODING)
            except UnicodeEncodeError as exc:
                raise ValueError(f'{SIDES[side]} briefing, line {line + 1}: '
                                 'use characters supported by the game (Mac Roman).') from exc
            if any(byte < 32 or byte == 127 for byte in encoded):
                raise ValueError(f'{SIDES[side]} briefing, line {line + 1}: '
                                 'tabs and control characters are not supported.')
            if len(encoded) >= LINE_BYTES:
                raise ValueError(f'{SIDES[side]} briefing, line {line + 1}: '
                                 'the maximum is 127 characters.')
            offset = _line_offset(side, line)
            old = data[offset:offset + LINE_BYTES]
            if encoded != old.split(b'\0', 1)[0]:
                patches.append((offset, encoded.ljust(LINE_BYTES, b'\0'), SIDES[side]))
    return patches
