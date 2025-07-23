#!/usr/bin/env python3
"""
hello_world_sd_inpaint.py

Simple Stable Diffusion inpainting demo using Hugging Face Diffusers.
"""
from PIL import Image
import torch
from diffusers import AutoPipelineForInpainting

# --- Hardcoded paths and parameters ---
img_path    = "./output/20250719_130322/test_input2.png"
mask_path   = "./output/20250719_130322/test_mask2.png"
prompt_text = "A parchment paper map with black ink illustrations"
output_path = "./output/20250719_130322/sd_inpainted_xl.png"
model_id = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
num_steps   = 10
guidance    = 7.5

# --- Load pipeline ---
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = AutoPipelineForInpainting.from_pretrained(
    model_id,
    torch_dtype=torch.float16 if device=="cuda" else torch.float32,
    variant="fp16"  # if using FP16; drop for FP32
).to(device)

# --- Load images ---
init_image = Image.open(img_path).convert("RGB")
mask_image = Image.open(mask_path).convert("L")

# --- Run inpainting ---
result = pipe(
    prompt=prompt_text,
    image=init_image,
    mask_image=mask_image,
    guidance_scale=guidance,
    num_inference_steps=num_steps,
).images[0]

# --- Save output ---
result.save(output_path)
print(f"[✔] Inpainted image saved to {output_path}")
