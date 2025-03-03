#!/bin/bash -l
#SBATCH --job-name=fibroblasts
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --output=slurm/out.%j.out
#SBATCH --error=slurm/error.%j.err

# -------------------------------------------------------------------------
# Script Name: run_fibroblast_pipeline.sh
# Description:
#   A Slurm batch script that:
#     1) cd's to the project root directory
#     2) Runs patch_prep.py to tile/prep the WSI
#     3) Runs HEIP inference
#     4) Merges patch predictions
#     5) Classifies fibroblasts
#     6) Dilates fibroblast outlines
# -------------------------------------------------------------------------

# Move to project root (parent directory of 'batchscripts/')
cd "$(dirname "$0")/.."

# Load modules and activate Conda environment (example)
module load gcc/12.1.0
#module load cuda/12.1
module load miniconda3
source /apps/software/gcc-12.1.0/miniconda3/23.1.0/bin/activate Fibro

# Parse argument: e.g., my_slide.svs
SLIDE_NAME=$1
BASE_NAME="${SLIDE_NAME%.svs}"

# -----------------------------------------------
# Step 1: Tiling & Preprocessing with patch_prep.py
# -----------------------------------------------
echo "==> Tiling and Preprocessing"
python scripts/patch_prep.py "${SLIDE_NAME}"

# -----------------------------------------------
# Step 2: HEIP Inference
# -----------------------------------------------
CKPT_PATH="./segmentation_model/last.ckpt"
DATA_PATH="./patches/${BASE_NAME}_patches/sample1_patches"
RESULT_PATH="./patches_seg/${BASE_NAME}_seg"
HEIP_PATH="/path/to/HEIP"  # Update as needed

echo "==> Running HEIP Inference"
export PYTHONPATH="${HEIP_PATH}:${PYTHONPATH}"
python "$HEIP_PATH/src/scripts/infer_wsi.py" \
    --in_dir "$DATA_PATH" \
    --res_dir "$RESULT_PATH" \
    --ckpt_path "$CKPT_PATH" \
    --device "cpu" \
    --n_devices 8 \
    --exp_name "infer_test1" \
    --exp_version "try1" \
    --batch_size 8 \
    --padding 120 \
    --stride 80 \
    --patch_size 256 \
    --classes_type "bg,neoplastic,inflammatory,connective,dead,epithel" \
    --geo_format "qupath" \
    --offsets 1

# -----------------------------------------------
# Step 3: Merge Patch Predictions
# -----------------------------------------------
echo "==> Merging Patch Predictions"
python scripts/patch_merging.py "${BASE_NAME}"

# -----------------------------------------------
# Step 4: Fibroblast Classification
# -----------------------------------------------
echo "==> Classifying Fibroblasts"
python scripts/run_fibroblast_classifier.py "${BASE_NAME}"

# -----------------------------------------------
# Step 5: Fibroblast Dilation
# -----------------------------------------------
echo "==> Dilating Fibroblast Outlines"
python scripts/fibroblast_dilation.py "${BASE_NAME}"

echo "Pipeline complete!"
