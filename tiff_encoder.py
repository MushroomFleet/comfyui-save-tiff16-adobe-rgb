"""
Minimal TIFF 6.0 encoder for uncompressed RGB images.
Supports 8-bit and 16-bit per channel.
Optionally embeds an ICC profile (tag 34675) for color-managed output.

Zero external dependencies beyond numpy.
"""

import struct
import numpy as np

TAG_IMAGE_WIDTH = 256
TAG_IMAGE_LENGTH = 257
TAG_BITS_PER_SAMPLE = 258
TAG_COMPRESSION = 259
TAG_PHOTOMETRIC = 262
TAG_STRIP_OFFSETS = 273
TAG_SAMPLES_PER_PIXEL = 277
TAG_ROWS_PER_STRIP = 278
TAG_STRIP_BYTE_COUNTS = 279
TAG_X_RESOLUTION = 282
TAG_Y_RESOLUTION = 283
TAG_ICC_PROFILE = 34675

TYPE_BYTE = 1
TYPE_SHORT = 3
TYPE_LONG = 4
TYPE_RATIONAL = 5


def encode_tiff(pixel_data, width, height, bits_per_sample=16, icc_profile=None):
    """
    Encode pixel data as an uncompressed TIFF 6.0 file.

    Args:
        pixel_data: numpy array of shape (H, W, 3), dtype uint16 or uint8
        width:      image width in pixels
        height:     image height in pixels
        bits_per_sample: 8 or 16
        icc_profile: bytes of ICC profile data, or None

    Returns:
        bytes of the complete TIFF file
    """
    samples_per_pixel = 3
    bytes_per_sample = bits_per_sample // 8
    strip_byte_count = width * height * samples_per_pixel * bytes_per_sample

    has_icc = icc_profile is not None
    num_tags = 12 if has_icc else 11

    ifd_offset = 8
    ifd_size = 2 + num_tags * 12 + 4  # count + entries + next-IFD pointer

    extra_data_offset = ifd_offset + ifd_size
    bits_per_sample_offset = extra_data_offset
    x_resolution_offset = bits_per_sample_offset + 6   # 3 x uint16
    y_resolution_offset = x_resolution_offset + 8      # 1 x rational
    after_resolution = y_resolution_offset + 8          # 1 x rational

    icc_profile_offset = 0
    if has_icc:
        icc_profile_offset = after_resolution
        after_resolution += len(icc_profile)
        # Align to 2-byte boundary for uint16 pixel data
        if bits_per_sample == 16 and after_resolution % 2 != 0:
            after_resolution += 1

    pixel_data_offset = after_resolution
    total_size = pixel_data_offset + strip_byte_count

    buf = bytearray(total_size)

    def write_u16(off, val):
        struct.pack_into('<H', buf, off, val)

    def write_u32(off, val):
        struct.pack_into('<I', buf, off, val)

    offset = 0

    # --- Header ---
    buf[offset] = 0x49; offset += 1   # 'I'
    buf[offset] = 0x49; offset += 1   # 'I' — little-endian byte order
    write_u16(offset, 42); offset += 2   # TIFF magic number
    write_u32(offset, ifd_offset); offset += 4

    # --- IFD ---
    write_u16(offset, num_tags); offset += 2

    def write_tag(tag, typ, count, value):
        nonlocal offset
        write_u16(offset, tag);   offset += 2
        write_u16(offset, typ);   offset += 2
        write_u32(offset, count); offset += 4
        if typ == TYPE_SHORT and count == 1:
            write_u16(offset, value)
            write_u16(offset + 2, 0)
        else:
            write_u32(offset, value)
        offset += 4

    # IFD entries — must be sorted by tag number
    write_tag(TAG_IMAGE_WIDTH,      TYPE_LONG,  1, width)
    write_tag(TAG_IMAGE_LENGTH,     TYPE_LONG,  1, height)
    write_tag(TAG_BITS_PER_SAMPLE,  TYPE_SHORT, 3, bits_per_sample_offset)
    write_tag(TAG_COMPRESSION,      TYPE_SHORT, 1, 1)   # no compression
    write_tag(TAG_PHOTOMETRIC,      TYPE_SHORT, 1, 2)   # RGB
    write_tag(TAG_STRIP_OFFSETS,    TYPE_LONG,  1, pixel_data_offset)
    write_tag(TAG_SAMPLES_PER_PIXEL,TYPE_SHORT, 1, 3)
    write_tag(TAG_ROWS_PER_STRIP,   TYPE_LONG,  1, height)
    write_tag(TAG_STRIP_BYTE_COUNTS,TYPE_LONG,  1, strip_byte_count)
    write_tag(TAG_X_RESOLUTION,     TYPE_RATIONAL, 1, x_resolution_offset)
    write_tag(TAG_Y_RESOLUTION,     TYPE_RATIONAL, 1, y_resolution_offset)
    if has_icc:
        write_tag(TAG_ICC_PROFILE,  TYPE_BYTE, len(icc_profile), icc_profile_offset)

    # Next IFD offset (none)
    write_u32(offset, 0); offset += 4

    # --- Extra data ---

    # BitsPerSample: 3 x SHORT
    write_u16(offset, bits_per_sample); offset += 2
    write_u16(offset, bits_per_sample); offset += 2
    write_u16(offset, bits_per_sample); offset += 2

    # XResolution: 72/1
    write_u32(offset, 72); offset += 4
    write_u32(offset, 1);  offset += 4

    # YResolution: 72/1
    write_u32(offset, 72); offset += 4
    write_u32(offset, 1);  offset += 4

    # ICC Profile data
    if has_icc:
        buf[icc_profile_offset:icc_profile_offset + len(icc_profile)] = icc_profile

    # Pixel data — interleaved RGB, little-endian
    if bits_per_sample == 16:
        pixel_bytes = pixel_data.reshape(-1).astype(np.dtype('<u2')).tobytes()
    else:
        pixel_bytes = pixel_data.reshape(-1).astype(np.uint8).tobytes()
    buf[pixel_data_offset:pixel_data_offset + strip_byte_count] = pixel_bytes

    return bytes(buf)
