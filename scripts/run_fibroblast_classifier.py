#!/usr/bin/env python3
"""
Script Name: run_fibroblast_classifier.py
Description:
  Loads a pre-trained fibroblast classifier (Random Forest) from the
  "classification_model" directory, processes a specified GeoJSON file,
  and outputs a new GeoJSON containing only fibroblast cells.

Usage:
  python run_fibroblast_classifier.py <slide_name>

Required Arguments:
  slide_name  The base name used to locate the input GeoJSON file:
              e.g., ./cells/<slide_name>.geojson

Output:
  - ./cells/<slide_name>_fibroblasts.geojson (fibroblast-only)
"""

import os
import sys
import json
import numpy as np
from joblib import load
from skimage.measure import regionprops, label
from skimage.draw import polygon
from tqdm import tqdm

# ---------------------------------------------------------------------
# Helper Function: generate_morphological_features
# ---------------------------------------------------------------------
def generate_morphological_features(coords, k=10):
    """
    Given polygon coordinates, generate morphological features:
      1. area
      2. perimeter
      3. area_ratio (perimeter / area)
      4. major_axis_length
      5. minor_axis_length
      6. axis_ratio (major_axis_length / minor_axis_length)
      7. convexity (convex_area / area)
      8. circularity (4π * area / perimeter^2)

    'k' is a padding factor for bounding the polygon in an image mask.
    """
    coords = np.array(coords)

    # Calculate dynamic bounds with padding
    min_x, min_y = np.min(coords, axis=0) - k
    max_x, max_y = np.max(coords, axis=0) + k

    # Normalize coordinates to local image space
    coords[:, 0] -= min_x
    coords[:, 1] -= min_y

    # Define dynamic image size
    image_shape = (int(max_y - min_y), int(max_x - min_x))

    # Create a blank binary mask for the polygon
    rr, cc = polygon(coords[:, 1], coords[:, 0], image_shape)
    mask = np.zeros(image_shape, dtype=bool)
    mask[rr, cc] = True

    # Use regionprops to extract features
    labeled_mask = label(mask)
    if not labeled_mask.any():
        # Return default values if no valid region
        return [0, 0, 0, 0, 0, 0, 0, 0]

    props = regionprops(labeled_mask)[0]
    area = props.area
    perimeter = props.perimeter
    area_ratio = perimeter / area if area > 0 else 0
    major_axis_length = props.major_axis_length
    minor_axis_length = props.minor_axis_length
    axis_ratio = (major_axis_length / minor_axis_length) if minor_axis_length > 0 else 0
    convex_area = props.convex_area
    convexity = convex_area / area if area > 0 else 0
    circularity = (4 * np.pi * area) / (perimeter**2) if perimeter > 0 else 0

    return [
        area,
        perimeter,
        area_ratio,
        major_axis_length,
        minor_axis_length,
        axis_ratio,
        convexity,
        circularity
    ]

# ---------------------------------------------------------------------
# Helper Function: process_json_file
# ---------------------------------------------------------------------
def process_json_file(input_file, output_file, trained_model):
    """
    Reads a GeoJSON file containing many cell polygons ("features"),
    classifies each as fibroblast or not, and writes out only the
    fibroblast cells to a new GeoJSON file.
    """
    # Load the source GeoJSON file
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Extract the list of features
    if "features" not in data:
        raise ValueError("The input JSON does not contain a 'features' key.")

    features = data["features"]
    fibro_cells = []  # Collect only fibroblast cells

    # Process each cell in the JSON file
    for feature in tqdm(features, desc="Processing Cells"):
        # Check geometry validity
        if "geometry" not in feature or "coordinates" not in feature["geometry"]:
            continue

        coords = feature["geometry"]["coordinates"]
        if not isinstance(coords, list) or len(coords) == 0:
            continue

        # Extract the polygon
        coords_array = np.array(coords[0])

        # Generate morphological features
        morph_features = generate_morphological_features(coords_array)

        # Predict if the cell is a fibroblast
        prediction = trained_model.predict([morph_features])[0]  # Model expects 2D array
        if prediction == "fibroblast":
            # Assign properties for fibroblast classification
            feature["properties"] = {
                "isLocked": "false",
                "classification": "fibroblast",
                "color": [255, 0, 0]  # Example color code
            }
            fibro_cells.append(feature)

    # Prepare new GeoJSON structure
    output_data = {
        "type": "FeatureCollection",
        "features": fibro_cells
    }

    # Ensure the target folder exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write fibroblast-only GeoJSON
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=4)

# ---------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Require exactly one argument: <slide_name>
    if len(sys.argv) != 2:
        print("Usage: python run_fibroblast_classifier.py <slide_name>")
        sys.exit(1)

    slide_name = sys.argv[1]

    # Load the pretrained model from the classification_model directory
    model_path = os.path.join("classification_model", "fibroblast_classifier_vehicle.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model not found at: {model_path}")

    trained_model = load(model_path)
    print(f"Loaded fibroblast classifier from: {model_path}")

    # Define the input and output paths
    input_file = os.path.join("cells", f"{slide_name}.geojson")
    output_file = os.path.join("cells", f"{slide_name}_fibroblasts.geojson")

    # Check for input file existence
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    # Classify fibroblast cells
    print("Processing and classifying cells...")
    process_json_file(input_file, output_file, trained_model)
    print(f"Fibroblast-only JSON file written to: {output_file}")
