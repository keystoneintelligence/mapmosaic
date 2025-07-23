import os
import base64
import mimetypes
from datetime import datetime
from typing import List, Optional
from PIL import Image
import openai
from openai import OpenAI

class OpenAIImageGenerator:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.api_key = api_key

    @staticmethod
    def _process_image(image_path: str) -> Optional[bytes]:
        """Load an image from disk."""
        if not os.path.exists(image_path):
            print(f"Warning: File not found at '{image_path}'. Skipping.")
            return None
        try:
            with open(image_path, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"Error loading image '{image_path}': {e}")
            return None

    def generate_rough_draft_image(self, working_dir: str, reference_image: str, map_description: str) -> Optional[str]:
        seed_image = None

        prompt = (
            f"Generate a top-down map inspired by the structure of the reference image. "
            f"Do not recreate the reference image exactly, but use it as guidance for layout, shapes, and color placement. "
            f"Include rich visual detail, depth, and texture. The description for the style of the map tile to generate is {map_description}. Do not include text, letters, or symbols of any kind."
        )

        retries = 0
        while seed_image is None:
            seed_image = self.generate_image(
                prompt=prompt,
                output_path=working_dir,
                reference_images=[reference_image],
                prefix="rough_draft",
                quality="low",
            )
            retries += 1
            if retries >= 3:
                raise ValueError("Failed to call OpenAI")

        return seed_image

    def generate_seed_image(self, idx: int, working_dir: str, reference_image: str, map_description: str) -> Optional[str]:
        seed_image = None

        prompt = (
            f"Generate a top-down map tile inspired by the structure of the reference image. "
            f"Do not recreate the reference image exactly, but use it as guidance for layout, shapes, and color placement. "
            f"Include rich visual detail, depth, and texture. The description for the style of the map tile to generate is {map_description}."
        )

        retries = 0
        while seed_image is None:
            seed_image = self.generate_image(
                prompt=prompt,
                output_path=working_dir,
                reference_images=[reference_image],
                prefix=f"seed_{idx}",
                quality="low",
            )
            retries += 1
            if retries >= 3:
                raise ValueError("Failed to call OpenAI")

        return seed_image

    def generate_mosaic_image(self, idx: int, working_dir: str, reference_image: str, mask_path: str, map_description: str) -> Optional[str]:
        mosaic_image = None

        prompt = (
            f"Fill in the missing portion of the top-down map tile. "
            f"Use the color in the reference image as guidance. Try to keep the currently populated portion of the image as unedited as possible. "
            f"The description for the style of the map tile is {map_description}, which should be kept consistent."
        )

        retries = 0
        while mosaic_image is None:
            mosaic_image = self.generate_image(
                prompt=prompt,
                output_path=working_dir,
                reference_images=[reference_image],
                prefix=f"mosaic_{idx}",
                input_fidelity="high",
                quality="low",
                mask=open(mask_path, "rb"),
            )
            retries += 1
            if retries >= 3:
                raise ValueError("Failed to call OpenAI")

        return mosaic_image

    def generate_image(
        self,
        prompt: str,
        output_path: str,
        reference_images: Optional[List[str]] = None,
        size: str = "1024x1024",
        prefix: str = "generated",
        model: str = "gpt-image-1",
        **kwargs,
    ) -> Optional[str]:
        """
        Generate an image using OpenAI's image model and save to disk.
        If reference_images are provided, they're used for image edits.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Open the reference image(s) as file handles, not bytes.
        image_files = []
        for path in reference_images or []:
            if os.path.exists(path):
                try:
                    image_files.append(open(path, "rb"))
                except Exception as e:
                    print(f"Error opening reference image {path}: {e}")
        if not image_files:
            print("Warning: no valid reference images found; falling back to text-only generation.")

        # Call the edit endpoint with a file handle
        # (if you want pure variations without a mask, you can use images.variations.create instead)
        try:
            result = openai.images.edit(
                model=model,
                image=image_files[0] if image_files else None,
                prompt=prompt,
                n=1,
                size=size,
                **kwargs,
            )
        finally:
            # close any open file handles
            for f in image_files:
                f.close()

        # decode & save
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = os.path.join(output_path, f"{prefix}_{timestamp}.png")
        with open(final_path, "wb") as f:
            f.write(image_bytes)

        return final_path

    def test_api_key(self) -> bool:
        """
        Verify the OpenAI API key by attempting to list models.
        Returns True if the call succeeds, False otherwise.
        """
        client = OpenAI(api_key=self.api_key)
        try:
            # This will throw if the key is invalid or unauthorized
            client.models.list()
            return True
        except Exception as e:
            raise ValueError(f"OpenAI API key test failed: {e}")
