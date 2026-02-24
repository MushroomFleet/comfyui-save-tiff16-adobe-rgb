# ComfyUI Save TIFF (16-bit, Adobe RGB)

A custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) that saves images as **16-bit TIFF files** with optional **Adobe RGB (1998)** color space conversion and embedded ICC profiles.

## Why 16-bit TIFF?

Standard 8-bit PNG output discards tonal information. 16-bit TIFF preserves the full dynamic range of your generated images — 65,536 levels per channel instead of 256 — making it ideal for:

- **Print-ready workflows** that demand Adobe RGB and high bit-depth
- **Post-processing** in Photoshop, Lightroom, or DaVinci Resolve without banding
- **Archival storage** where quality loss is unacceptable
- **Color-managed pipelines** that require embedded ICC profiles

## Features

- **16-bit per channel** — saves the full precision of ComfyUI's internal float32 pipeline
- **sRGB or Adobe RGB (1998)** — selectable color space with accurate conversion
- **Embedded ICC profile** — Adobe RGB ICC v2.1 profile built from scratch and embedded directly in the TIFF
- **Proper color math** — linearizes sRGB, applies a 3x3 matrix transform through CIE XYZ (D65), then Adobe RGB gamma encodes
- **Zero image library dependencies** — custom TIFF 6.0 encoder using only NumPy (no Pillow/PIL required for writing)
- **Drop-in replacement** — works just like the built-in Save Image node with the same filename prefix and counter behavior

## Node Reference

| Field | Details |
|---|---|
| **Node name** | Save TIFF (16-bit) |
| **Category** | Save TIFF |
| **Input** | `IMAGE` — any ComfyUI image pipeline output |
| **Parameters** | `filename_prefix` (string, default `ComfyUI`), `color_space` (sRGB or Adobe RGB (1998)) |
| **Output** | `.tiff` files written to your ComfyUI output directory |

## Installation

Clone this repository into your ComfyUI `custom_nodes` folder:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/MushroomFleet/comfyui-save-tiff16-adobe-rgb.git
```

Install the dependency:

```bash
pip install -r ComfyUI/custom_nodes/comfyui-save-tiff16-adobe-rgb/requirements.txt
```

Restart ComfyUI. The **Save TIFF (16-bit)** node will appear under the **Save TIFF** category.

## Usage

1. Add the **Save TIFF (16-bit)** node to your workflow
2. Connect any `IMAGE` output to its input
3. Set a `filename_prefix` (files are saved as `prefix_00001_.tiff`, `prefix_00002_.tiff`, etc.)
4. Choose your **color space**:
   - **sRGB** — standard web/screen color space (default)
   - **Adobe RGB (1998)** — wider gamut for print and professional editing, with an embedded ICC profile

## Live Demo

Try the standalone browser version (no ComfyUI required):

**[https://scuffedepoch.com/adobe-tiff16/](https://scuffedepoch.com/adobe-tiff16/)**

## 📚 Citation

### Academic Citation

If you use this codebase in your research or project, please cite:

```bibtex
@software{comfyui_save_tiff16_adobe_rgb,
  title = {ComfyUI Save TIFF (16-bit, Adobe RGB): High bit-depth TIFF output with Adobe RGB color space support for ComfyUI},
  author = {Drift Johnson},
  year = {2025},
  url = {https://github.com/MushroomFleet/comfyui-save-tiff16-adobe-rgb},
  version = {1.0.0}
}
```

### Donate:

[![Ko-Fi](https://cdn.ko-fi.com/cdn/kofi3.png?v=3)](https://ko-fi.com/driftjohnson)
