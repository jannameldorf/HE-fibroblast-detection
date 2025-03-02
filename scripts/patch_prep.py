#!/usr/bin/env python3
"""
Script Name: patch_prep.py
Description:
  This script takes a whole-slide image (WSI) in .svs format and uses histoprep 
  to generate patches. It applies a tissue mask to identify relevant regions, 
  renames the patch image files, and moves them to a final subfolder structure:
    patches/<slide_name>_patches

Usage:
  python patch_prep.py <slide_name.svs>

Required Argument:
  slide_name.svs  The name of the SVS file located in the '/slides' directory.

Output:
  - A directory containing patch image files and metadata for downstream analysis.
"""

import histoprep as hp
import os
import pandas as pd
from PIL import Image, ImageDraw
import cv2
import numpy as np
import matplotlib.pyplot as plt
import shutil
import sys

# ---------------------------------------------------------------------
# Check if exactly one argument (the slide name) is provided.
# ---------------------------------------------------------------------
if len(sys.argv) != 2:
    print("Usage: python patch_prep.py <slide_name.svs>")
    sys.exit(1)

# ---------------------------------------------------------------------
# Set up paths and input variables.
# ---------------------------------------------------------------------
path = './slides'  # Folder containing the slide files
sample = sys.argv[1]  # Slide name passed as an argument
sample_name = os.path.join(path, sample)
output_folder = './patches'
print('Patching sample:', sample)
print('Path:', sample_name)

# Extract the base name (no extension) from the sample name
sample_base = os.path.splitext(sample)[0]

# ---------------------------------------------------------------------
# Create histoprep SlideReader and generate patches (tiles).
# ---------------------------------------------------------------------
reader = hp.SlideReader(sample_name)
threshold, tissue_mask = reader.get_tissue_mask(level=-1)

# Obtain coordinates for patching
tile_coordinates = reader.get_tile_coordinates(
    tissue_mask,
    width=1250,
    overlap=0,
    max_background=0.92
)

# Save the tiles (patches) along with some metadata
metadata = reader.save_regions(
    output_folder,
    coordinates=tile_coordinates,
    threshold=threshold,
    image_format="png",
    quality=100,
    save_metrics=True,
)
print(f'Sample: {sample}, patching complete!')

# ---------------------------------------------------------------------
# Update paths for metadata and create references for the thumbnail.
# ---------------------------------------------------------------------
sample_metadata_path = os.path.join(output_folder, sample_base, 'metadata.parquet')
output_folder_sample = os.path.join(output_folder, sample_base)
print(f'Preprocessing sample: {sample}')
print(f'Metadata path: {sample_metadata_path}')

# Read metadata
metadata = pd.read_parquet(sample_metadata_path, engine='pyarrow')

# Load the thumbnail image
thumbnail_path = os.path.join(output_folder_sample, 'thumbnail.jpeg')
thumbnail = Image.open(thumbnail_path).convert('RGB')
annotated_thumbnail = thumbnail.copy()
annotated = ImageDraw.Draw(annotated_thumbnail)

# ---------------------------------------------------------------------
# Generate tissue mask for the thumbnail to identify main tissue regions.
# ---------------------------------------------------------------------
thumb = hp.SlideReader(thumbnail_path)
_, mask = thumb.get_tissue_mask()

kernel_size = (30, 30)
mask2 = cv2.dilate(mask, np.ones(kernel_size, np.uint8), iterations=5)

# Extract contours
contours, _ = cv2.findContours(mask2, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

# Filter contours based on area to focus on main tissue regions
areas = np.array([cv2.contourArea(x) for x in contours])
max_area = max(areas)
min_area = max_area - (max_area * 40 / 100)
bounding_boxes = [cv2.boundingRect(cnt) for cnt in contours if cv2.contourArea(cnt) >= min_area]

# ---------------------------------------------------------------------
# Rename patch files to remove 'w1250_h1250' from filenames.
# ---------------------------------------------------------------------
for i in range(len(metadata)):
    old_name = os.path.join(
        output_folder_sample, 
        'tiles', 
        f'x{metadata["x"][i]}_y{metadata["y"][i]}_w1250_h1250.png'
    )
    new_name = os.path.join(
        output_folder_sample,
        'tiles',
        f'x-{metadata["x"][i]}_y-{metadata["y"][i]}.png'
    )
    shutil.move(old_name, new_name)

# ---------------------------------------------------------------------
# Move all generated patches to the final output directory:
#   ./patches/<slide_name>_patches/sample1_patches
# ---------------------------------------------------------------------
final_folder = os.path.join(output_folder, f'{sample_base}_patches', 'sample1_patches')
os.makedirs(final_folder, exist_ok=True)

tiles_folder = os.path.join(output_folder_sample, 'tiles')
for file in os.listdir(tiles_folder):
    shutil.move(os.path.join(tiles_folder, file), final_folder)

print("Processing complete! Patches saved to:", final_folder)
