from simple_lama_inpainting import SimpleLama
from PIL import Image

simple_lama = SimpleLama()

img_path = "./output/20250719_130322/test_input.png"
mask_path = "./output/20250719_130322/test_mask2.png"

image = Image.open(img_path).convert('RGB')
mask = Image.open(mask_path).convert('L')

result = simple_lama(image, mask)
result.save("./output/20250719_130322/inpainted2.png")
