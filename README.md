# H&E Fibroblast Detection

## Introduction

This repository contains the fibroblast detection pipeline accompanying the paper:

**NNMT inhibition prevents cancer-associated fibroblast-mediated immunosuppression (not yet published)**

The pipeline detects fibroblasts in H&E whole-slide images (WSIs) using morphological features. It leverages the HEIP toolkit to segment nuclei in the H&E images, then applies a Random Forest classifier (trained on specific morphological features directed by a pathologist) to identify fibroblasts. Finally, the pipeline dilates fibroblast outlines to approximate cytoplasm boundaries, producing output files loadable in QuPath (v0.5+ recommended).
## Installation
1) Clone This Repository

```
git clone git@github.com:jannameldorf/HE-fibroblast-detection.git
```

2) Move Into the Project Directory

```
cd <project path>/HE-fibroblast-detection/
```

3) Create a (Recommended) Python Environment

You need Python >3.7. Below are two examples (Conda or venv):

**Conda Example**

```
conda create --name Fibro python=3.9
conda activate Fibro
```

**Python venv Example**

```
python3 -m venv Fibro
source Fibro/bin/activate
pip install --upgrade pip
```

4) Install Dependencies

```
pip install -r requirements.txt
```

Note: This project requires [HEIP](https://github.com/ValeAri/HEIP) to be installed and accessible. Follow instructions from the HEIP repository to install and/or set up the HEIP segmentation toolkit. And set the path to your local HEIP folder in the batchscripts accordingly.


5) Load the Segmentation Model

The HEIP segmentation model must be located in the segmentation_model/ folder. For example, we assume a file like last.ckpt is present:

<pre>
segmentation_model/
└── last.ckpt
</pre>

For loading the correct model please verify on their [Github page](https://github.com/ValeAri/HEIP) (or load the file [here](https://www.dropbox.com/scl/fi/jd3td009blmjv0lla0u80/last.ckpt?rlkey=jszlw4gqrklv85uq4r0lw5cuh&dl=0)).

6) Load the Fibroblast Classification Model

A pre-trained Random Forest model is also stored in classification_model/fibroblast_classifier.joblib (or a similarly named file). This model is used in run_fibroblast_classifier.py to label cells as fibroblasts. The models can be loaded [here](https://uchicago.box.com/s/4jfd7zaezh55z3khv6ftwmhxrjefc6rz).

## Folder Structure & Requirements

The pipeline expects a directory layout like this (when running the Slurm/batch script or the Python scripts):


<pre>
project/
├── batchscripts/
│    └── run_fibroblast_pipeline.sh     # Slurm script orchestrating the pipeline
├── slides/
│    └── my_slide.svs                   # WSI in SVS format
├── patches/                            # Tiled patches will be created here by patch_prep.py
├── patches_seg/                        # HEIP segmentation outputs
├── cells/                              # All GeoJSON file outputs for QuPath
├── segmentation_model/
│    ├── last.ckpt                      # HEIP segmentation checkpoint
├── classification_model/
│    └── fibroblast_classifier.joblib   # Fibroblast classification model (or similar)
├── scripts/
│    ├── patch_prep.py
│    ├── patch_merging.py
│    ├── run_fibroblast_classifier.py
│    └── fibroblast_dilation.py
└── requirements.txt
</pre>

**Notes**

WSI Format: The pipeline uses .svs files. If your WSI is in another format, convert or adapt the scripts accordingly. The recommended slide magnification is 40×.
Multiple Classifier Models: The repository can works with different classification models trained under various settings (e.g. untreated vs. treated tissue). The recommended model (e.g., fibroblast_classifier_vehicle.joblib) is used by default. You can change models by editing run_fibroblast_classifier.py.

## Usage

Navigate to the batchscripts folder:

```
cd <project path>/batchscripts
```

Submit the Pipeline (Slurm Example):

```
sbatch run_fibroblast_pipeline.sh <slide_name.svs>
```

Where <slide_name.svs> is located in slides/. The pipeline will:
1. Tile/Prep the WSI (generates patches in patches/).
2. Run HEIP to segment nuclei in patches_seg/.
3. Merge cell predictions into a single GeoJSON (patch_merging.py).
4. Classify fibroblasts using the Random Forest model (run_fibroblast_classifier.py).
5. Dilate fibroblast outlines to approximate cytoplasm (fibroblast_dilation.py).

Output:
The final outlines are saved in cells/<slide_name>_fibroblasts_dilated.geojson, which can be imported into QuPath v0.5+ for visualization.

**Notes**

Depending on slide size, tissue coverage, and available hardware, the pipeline can be time-intensive. GPU acceleration is supported by HEIP if available, reducing inference time significantly.

For questions related to this codebase and pipeline, please open an Issue or contact the corresponding authors as listed in the paper:\
NNMT inhibition prevents cancer-associated fibroblast-mediated immunosuppression (not yet published)

Thank you for using this pipeline!