#!/usr/bin/env python3
"""
Script Name: fibroblast_dilation.py
Description:
  This script takes an input GeoJSON file of detected fibroblast polygons, 
  dilates them (scales their coordinates) to approximate cytoplasm boundaries, 
  and adjusts overlaps with other cells. The final dilated fibroblast outlines 
  are saved to a new GeoJSON.

Usage:
  python fibroblast_dilation.py <slide_name>

Required Argument:
  slide_name        The base name of the slide or sample.

Outputs:
  - ./cells/<slide_name>_fibroblasts_dilated.geojson 
    (the final dilated fibroblast outlines)
"""

import json
import numpy as np
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import unary_union
from tqdm import tqdm
import sys
from scipy.spatial import KDTree
import os

# ---------------------------------------------------------------------
# Validate command-line argument
# ---------------------------------------------------------------------
if len(sys.argv) != 2:
    print("Usage: python fibroblast_dilation.py <slide_name>")
    sys.exit(1)

slide_name = sys.argv[1]

# ---------------------------------------------------------------------
# Define paths (all in ./cells/ directory)
# ---------------------------------------------------------------------
fibroblast_json_path = f'./cells/{slide_name}_fibroblasts.geojson'
all_cells_json_path  = f'./cells/{slide_name}.geojson'
output_path          = f'./cells/{slide_name}_fibroblasts_dilated.geojson'

# ---------------------------------------------------------------------
# Scaling and simplification factors
# ---------------------------------------------------------------------
scale_factor_fibroblast = 2.0  # Scale factor for fibroblast polygons
scale_factor_other      = 1.2  # Scale factor for all other cells
simplify_tolerance      = 1.0  # RDP simplification tolerance

# ---------------------------------------------------------------------
# Load the input GeoJSON files
# ---------------------------------------------------------------------
print("Loading JSON files...")
with open(fibroblast_json_path, 'r') as file:
    fibroblast_data = json.load(file)

with open(all_cells_json_path, 'r') as file:
    all_cells_data = json.load(file)

# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def calculate_centroid(geojson_polygon):
    """
    Return centroid (x, y) for a given GeoJSON polygon geometry.
    """
    geom = shape(geojson_polygon)
    return geom.centroid.x, geom.centroid.y

def scale_polygon(polygon_coords, scale_factor):
    """
    Scale polygon coordinates around their centroid by a given scale factor.
    """
    polygon_array = np.array(polygon_coords)
    centroid = polygon_array.mean(axis=0)
    scaled_polygon = centroid + (polygon_array - centroid) * scale_factor
    return scaled_polygon.tolist()

def filter_boundary_points(scaled_boundary, unscaled_fibro_boundary, unscaled_cell_boundary):
    """
    Keep scaled boundary points only if they are closer to the fibroblast 
    boundary. This helps preserve the 'fibroblast' outline without 
    encroaching on neighboring cells.
    """
    combined_boundaries = np.vstack([unscaled_fibro_boundary, unscaled_cell_boundary])
    kdtree = KDTree(combined_boundaries)

    num_fibro_points = len(unscaled_fibro_boundary)
    filtered_points = []

    for point in scaled_boundary:
        _, idx = kdtree.query(point)
        if idx < num_fibro_points:
            filtered_points.append(point)

    return filtered_points

# ---------------------------------------------------------------------
# Scale fibroblast polygons
# ---------------------------------------------------------------------
print("Scaling fibroblast polygons...")
scaled_fibros = []
for feature in tqdm(fibroblast_data["features"], desc="Processing Fibroblasts"):
    coords = feature["geometry"]["coordinates"]
    if not coords or not isinstance(coords, list):
        continue

    scaled_coords = scale_polygon(coords[0], scale_factor_fibroblast)
    feature["geometry"]["coordinates"] = [scaled_coords]
    scaled_fibros.append(feature)

# ---------------------------------------------------------------------
# Scale all cell polygons
# ---------------------------------------------------------------------
print("Scaling all cell polygons...")
scaled_cells = []
for feature in tqdm(all_cells_data["features"], desc="Processing All Cells"):
    coords = feature["geometry"]["coordinates"]
    if not coords or not isinstance(coords, list):
        continue

    scaled_coords = scale_polygon(coords[0], scale_factor_other)
    feature["geometry"]["coordinates"] = [scaled_coords]
    scaled_cells.append(feature)

# ---------------------------------------------------------------------
# Calculate centroids of all scaled cells (for overlap handling)
# ---------------------------------------------------------------------
cell_centroids = [(calculate_centroid(cell["geometry"]), cell) for cell in scaled_cells]

# ---------------------------------------------------------------------
# Resolve overlaps between fibroblasts and nearby cells
# ---------------------------------------------------------------------
print("Resolving overlaps...")
non_overlapping_fibros = []

for i, fibro_feature in enumerate(tqdm(scaled_fibros, desc="Adjusting Fibroblast Boundaries")):
    fibro_polygon = shape(fibro_feature["geometry"])
    fibro_centroid = calculate_centroid(fibro_feature["geometry"])

    # Unscaled fibroblast boundary
    unscaled_fibro_boundary = np.array(
        shape(fibroblast_data["features"][i]["geometry"]).exterior.coords
    )

    # Find the 6 closest cells by centroid distance
    sorted_cells = sorted(
        cell_centroids,
        key=lambda x: ((x[0][0] - fibro_centroid[0])**2 + (x[0][1] - fibro_centroid[1])**2)**0.5
    )
    closest_cells = [cell for _, cell in sorted_cells[1:6]]  # skip the fibro itself at index 0

    # Check if one of the closest cells is fully inside the fibroblast polygon
    for cell_feature in closest_cells:
        cell_polygon = shape(cell_feature["geometry"])

        if cell_polygon.within(fibro_polygon):
            # Identify unscaled boundary of the enclosed cell
            cell_index = scaled_cells.index(cell_feature)
            unscaled_cell_boundary = np.array(
                shape(all_cells_data["features"][cell_index]["geometry"]).exterior.coords
            )

            # Filter the scaled fibroblast boundary to avoid overlap
            scaled_fibro_boundary = np.array(fibro_polygon.exterior.coords)
            filtered_points = filter_boundary_points(
                scaled_fibro_boundary,
                unscaled_fibro_boundary,
                unscaled_cell_boundary
            )

            # Recreate the fibroblast polygon with the filtered boundary
            if len(filtered_points) >= 3:  # valid polygon
                fibro_polygon = Polygon(filtered_points)

            break  # Only handle one enclosed cell per fibroblast

    # Simplify the polygon to smooth edges
    fibro_polygon = fibro_polygon.simplify(simplify_tolerance, preserve_topology=True)

    # If the result is a MultiPolygon, keep only the largest
    if fibro_polygon.geom_type == 'MultiPolygon':
        fibro_polygon = max(fibro_polygon.geoms, key=lambda p: p.area)

    # Update the fibroblast feature geometry
    fibro_feature["geometry"] = mapping(fibro_polygon)
    non_overlapping_fibros.append(fibro_feature)

# ---------------------------------------------------------------------
# Save the final dilated fibroblast outlines
# ---------------------------------------------------------------------
os.makedirs(os.path.dirname(output_path), exist_ok=True)
output_data = {
    "type": "FeatureCollection",
    "features": non_overlapping_fibros
}

with open(output_path, 'w') as file:
    json.dump(output_data, file, indent=4)

print(f"Processing complete! Dilated fibroblast outlines saved to {output_path}")
