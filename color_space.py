"""
Color space conversion: sRGB -> Adobe RGB (1998)

Pipeline:
  1. Undo sRGB transfer function (linearize)
  2. Linear sRGB -> Linear Adobe RGB (combined 3x3 matrix via CIE XYZ D65)
  3. Apply Adobe RGB gamma encode (563/256 = 2.19921875)

Both sRGB and Adobe RGB use D65 white point — no chromatic adaptation needed.
"""

import struct
import numpy as np

# --- sRGB Transfer Function ---

def srgb_to_linear(v):
    """Vectorized sRGB to linear. Input/output in [0, 1]."""
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))

# --- Adobe RGB (1998) Transfer Function ---

ADOBE_RGB_GAMMA_INV = 256.0 / 563.0  # 1 / 2.19921875

def linear_to_adobe_rgb(v):
    """Vectorized linear to Adobe RGB gamma encoding."""
    return np.power(np.maximum(v, 0.0), ADOBE_RGB_GAMMA_INV)

# --- Pre-computed combined matrix: sRGB linear -> Adobe RGB linear ---
# M_combined = XYZ_TO_ADOBE_RGB @ SRGB_TO_XYZ

M = np.array([
    [0.7151627, 0.2848373, 0.0000000],
    [0.0000000, 1.0000000, 0.0000000],
    [0.0000000, 0.0413880, 0.9586120],
], dtype=np.float64)

# --- Pixel Conversion ---

def convert_srgb_to_adobe_rgb(rgb):
    """
    Convert an image from sRGB to Adobe RGB (1998).

    Args:
        rgb: numpy float array, shape (H, W, 3), values in [0.0, 1.0]

    Returns:
        numpy float64 array, shape (H, W, 3), Adobe RGB values in [0.0, 1.0]
    """
    h, w, _ = rgb.shape
    linear = srgb_to_linear(rgb.astype(np.float64))
    flat = linear.reshape(-1, 3)
    adobe_linear = np.clip(flat @ M.T, 0.0, 1.0)
    adobe_gamma = linear_to_adobe_rgb(adobe_linear)
    return adobe_gamma.reshape(h, w, 3)


# --- Adobe RGB (1998) ICC Profile Builder ---

def build_adobe_rgb_icc_profile():
    """
    Build a minimal Adobe RGB (1998) ICC v2.1 profile from scratch.
    All multi-byte ICC fields are big-endian per the ICC specification.

    Returns:
        bytes of the complete ICC profile
    """
    def align4(n):
        return (n + 3) & ~3

    desc_text = b'Adobe RGB (1998)'
    cprt_text = b'No copyright'

    # Tag data sizes
    desc_size = 4 + 4 + 4 + len(desc_text) + 1 + 12 + 12  # 'desc' type structure
    xyz_tag_size = 20   # 'XYZ ' sig(4) + reserved(4) + 1 XYZ value(12)
    curve_tag_size = 16 # 'curv' sig(4) + reserved(4) + count(4) + u8Fixed8(2) + pad(2)
    cprt_size = 4 + 4 + len(cprt_text) + 1

    desc_aligned = align4(desc_size)
    cprt_aligned = align4(cprt_size)

    tag_count = 9
    tag_table_size = 4 + tag_count * 12
    header_size = 128
    data_start = header_size + tag_table_size

    # Calculate offsets for each tag's data
    desc_offset = data_start
    wtpt_offset = desc_offset + desc_aligned
    r_xyz_offset = wtpt_offset + xyz_tag_size
    g_xyz_offset = r_xyz_offset + xyz_tag_size
    b_xyz_offset = g_xyz_offset + xyz_tag_size
    r_trc_offset = b_xyz_offset + xyz_tag_size
    cprt_offset = r_trc_offset + curve_tag_size

    profile_size = cprt_offset + cprt_aligned

    buf = bytearray(profile_size)

    # --- Helpers (big-endian) ---
    def write_u32(off, val):
        struct.pack_into('>I', buf, off, val)

    def write_u16(off, val):
        struct.pack_into('>H', buf, off, val)

    def write_s15f16(off, val):
        struct.pack_into('>i', buf, off, round(val * 65536))

    def write_sig(off, sig):
        buf[off:off + 4] = sig.encode('ascii')

    def write_ascii(off, data):
        if isinstance(data, str):
            data = data.encode('ascii')
        buf[off:off + len(data)] = data

    # --- ICC Header (128 bytes) ---
    write_u32(0, profile_size)       # Profile size
    write_sig(4, 'ADBE')             # Preferred CMM
    write_u32(8, 0x02100000)         # Version 2.1.0
    write_sig(12, 'mntr')            # Device class: monitor
    write_sig(16, 'RGB ')            # Color space: RGB
    write_sig(20, 'XYZ ')            # PCS: XYZ
    # Creation date: 1999-06-03 00:00:00
    write_u16(24, 1999)
    write_u16(26, 6)
    write_u16(28, 3)
    write_u16(30, 0)
    write_u16(32, 0)
    write_u16(34, 0)
    write_sig(36, 'acsp')            # Profile file signature
    write_sig(40, 'APPL')            # Primary platform
    write_u32(44, 0)                 # Profile flags
    write_sig(48, 'none')            # Device manufacturer
    write_sig(52, 'none')            # Device model
    write_u32(64, 0)                 # Rendering intent (perceptual)
    # PCS illuminant D50: (0.9642, 1.0, 0.8249)
    write_s15f16(68, 0.9642)
    write_s15f16(72, 1.0000)
    write_s15f16(76, 0.8249)
    write_sig(80, 'ADBE')            # Profile creator

    # --- Tag Table ---
    off = header_size
    write_u32(off, tag_count)
    off += 4

    tags = [
        ('desc', desc_offset, desc_aligned),
        ('wtpt', wtpt_offset, xyz_tag_size),
        ('rXYZ', r_xyz_offset, xyz_tag_size),
        ('gXYZ', g_xyz_offset, xyz_tag_size),
        ('bXYZ', b_xyz_offset, xyz_tag_size),
        ('rTRC', r_trc_offset, curve_tag_size),  # shared curve
        ('gTRC', r_trc_offset, curve_tag_size),  # same offset
        ('bTRC', r_trc_offset, curve_tag_size),  # same offset
        ('cprt', cprt_offset, cprt_aligned),
    ]

    for sig, tag_off, tag_size in tags:
        write_sig(off, sig);    off += 4
        write_u32(off, tag_off); off += 4
        write_u32(off, tag_size); off += 4

    # --- Tag Data ---

    # desc — profile description
    off = desc_offset
    write_sig(off, 'desc'); off += 4
    write_u32(off, 0);     off += 4      # reserved
    write_u32(off, len(desc_text) + 1); off += 4
    write_ascii(off, desc_text); off += len(desc_text)
    buf[off] = 0  # null terminator

    # wtpt — white point (D65)
    off = wtpt_offset
    write_sig(off, 'XYZ '); off += 4
    write_u32(off, 0);     off += 4
    write_s15f16(off, 0.9505); off += 4
    write_s15f16(off, 1.0000); off += 4
    write_s15f16(off, 1.0890)

    # rXYZ — red primary (D50-adapted)
    off = r_xyz_offset
    write_sig(off, 'XYZ '); off += 4
    write_u32(off, 0);     off += 4
    write_s15f16(off, 0.6097559); off += 4
    write_s15f16(off, 0.3111145); off += 4
    write_s15f16(off, 0.0194702)

    # gXYZ — green primary (D50-adapted)
    off = g_xyz_offset
    write_sig(off, 'XYZ '); off += 4
    write_u32(off, 0);     off += 4
    write_s15f16(off, 0.2052401); off += 4
    write_s15f16(off, 0.6256714); off += 4
    write_s15f16(off, 0.0608902)

    # bXYZ — blue primary (D50-adapted)
    off = b_xyz_offset
    write_sig(off, 'XYZ '); off += 4
    write_u32(off, 0);     off += 4
    write_s15f16(off, 0.1492240); off += 4
    write_s15f16(off, 0.0632141); off += 4
    write_s15f16(off, 0.7445396)

    # rTRC — tone reproduction curve: gamma 2.19921875 (shared by g/bTRC)
    off = r_trc_offset
    write_sig(off, 'curv'); off += 4
    write_u32(off, 0);     off += 4     # reserved
    write_u32(off, 1);     off += 4     # count = 1 (parametric gamma)
    write_u16(off, 0x0233)              # u8Fixed8: 2 + 51/256 = 2.19921875

    # cprt — copyright
    off = cprt_offset
    write_sig(off, 'text'); off += 4
    write_u32(off, 0);     off += 4
    write_ascii(off, cprt_text)

    return bytes(buf)


_cached_profile = None

def get_adobe_rgb_icc_profile():
    """Return the Adobe RGB ICC profile, building and caching on first call."""
    global _cached_profile
    if _cached_profile is None:
        _cached_profile = build_adobe_rgb_icc_profile()
    return _cached_profile
