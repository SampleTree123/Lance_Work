import importlib.util
from pathlib import Path
from PIL import Image

spec = importlib.util.spec_from_file_location("probe_images", Path(__file__).parents[1] / "validate_wardrobe_probe_images_v1.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_uniform_black_and_white_are_not_evidence():
    for color in (0, 1, 255):
        assert not mod.image_content(Image.new("RGB", (128, 128), (color, color, color)))["pixel_content_valid"]


def test_nonblank_content_only_means_pixels_present():
    image = Image.new("RGB", (128, 128), "black")
    image.paste((180, 30, 30), (20, 20, 100, 100))
    assert mod.image_content(image)["pixel_content_valid"]
