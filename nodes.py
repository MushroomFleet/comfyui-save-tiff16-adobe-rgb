import os
import numpy as np
import folder_paths

from .color_space import convert_srgb_to_adobe_rgb, get_adobe_rgb_icc_profile
from .tiff_encoder import encode_tiff


class SaveTiff:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "color_space": (["sRGB", "Adobe RGB (1998)"], {"default": "sRGB"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "Save TIFF"

    def save_images(self, images, filename_prefix="ComfyUI", color_space="sRGB",
                    prompt=None, extra_pnginfo=None):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = (
            folder_paths.get_save_image_path(
                filename_prefix, self.output_dir,
                images[0].shape[1], images[0].shape[0]
            )
        )

        is_adobe_rgb = color_space == "Adobe RGB (1998)"
        icc_profile = get_adobe_rgb_icc_profile() if is_adobe_rgb else None

        results = list()
        for image in images:
            rgb = image.cpu().numpy()  # (H, W, 3), float32 in [0, 1]

            if is_adobe_rgb:
                rgb = convert_srgb_to_adobe_rgb(rgb)

            img16 = np.clip(np.round(rgb * 65535.0), 0, 65535).astype(np.uint16)

            file = f"{filename}_{counter:05}_.tiff"
            filepath = os.path.join(full_output_folder, file)

            tiff_bytes = encode_tiff(img16, img16.shape[1], img16.shape[0], 16, icc_profile)
            with open(filepath, 'wb') as f:
                f.write(tiff_bytes)

            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type,
            })
            counter += 1

        return {"ui": {"images": results}}


NODE_CLASS_MAPPINGS = {
    "SaveTiff": SaveTiff,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveTiff": "Save TIFF (16-bit)",
}
