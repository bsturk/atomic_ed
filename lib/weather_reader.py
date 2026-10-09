"""D-Day weather layouts used by the original engine and the 400-turn patch."""
import struct

NATIVE_SIZE = 794
EXTENDED_SIZE = 1222
CAPACITY = 400
NATIVE_DATES = ((97392, 97409), (97392, 97421), (97518, 97621),
                (97644, 97685), (97350, 97523), (97350, 97523), (97350, 97523))


def historical_weather_block(source):
    """Store the authored scenario interval with explicit absolute timestamps.

    Ground state remains a documented adaptation using D-Day's dry initial
    values; translating V4V's pre-scenario snow/ice simulation is separate.
    """
    weather = source.historical_weather
    if weather['mode'] != 0:
        raise ValueError('V4V generated-weather mode is not yet translated')
    count = weather['turns']
    if not 0 < count <= CAPACITY:
        raise ValueError('Scenario exceeds the patched 400-turn weather capacity')
    result = bytearray(EXTENDED_SIZE)
    # Repeat the last authored conditions in unused slots for calendar previews.
    temperatures = weather['temperatures_f'] + [weather['temperatures_f'][-1]] * (CAPACITY - count)
    codes = weather['weather_codes'] + [weather['weather_codes'][-1]] * (CAPACITY - count)
    struct.pack_into('<400h', result, 12, *temperatures)
    result[0x32c:0x4bc] = bytes(codes)
    start, end = struct.unpack_from('<2i', source.blocks[0], 0x16)
    struct.pack_into('<2i', result, 0x4be, start, end)
    return result


def validate_weather(block):
    if len(block) == NATIVE_SIZE:
        return
    if len(block) != EXTENDED_SIZE:
        raise ValueError('Unsupported D-Day weather block size')
    start, end = struct.unpack_from('<2i', block, 0x4be)
    if not 0 <= end - start < CAPACITY:
        raise ValueError('Weather dates exceed the patched 400-turn table')
    if any(code > 4 for code in block[0x32c:0x32c + end - start + 1]):
        raise ValueError('Invalid D-Day weather code')
