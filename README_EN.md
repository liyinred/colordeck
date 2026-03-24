# ColorDeck - Multiplex Immunofluorescence Image Registration and Merging Tool

English | [简体中文](README.md)

ColorDeck is a Python tool designed for the registration and merging of Multiplex Immunofluorescence (MIF) images. It automatically aligns microscope images from the same field of view but different channels, and combines them into a single comprehensive image.

---

## Features

- **Automatic Image Registration**: Precise image alignment based on the DAPI channel
- **Multiple Registration Algorithms**:
  - ECC (Enhanced Correlation Coefficient) - High-precision registration
  - Phase Correlation - Robust fallback method
- **Multiple Motion Models**: Supports Translation, Euclidean, and Affine transformations
- **Registration Quality Visualization**: Automatically generates registration preview images
- **Batch Processing**: Process all images in a folder with a single command
- **Automatic Size Matching**: Center-crops or resamples non-reference images to the reference size before registration
- **Overview Panel Output**: Generates a single panel containing every input fluorescence image plus the final merged result
- **Detailed Logging**: Records transformation matrices and registration scores for each image

---

## Installation

```bash
pip install opencv-python numpy
```

---

## Usage

### Basic Usage

```bash
python merge_mif_images.py
```

Run with default parameters. Input folder: `ColorDeck_test image`, reference image: `1_Spleen_DAPI_Lamin B1_RF 775_下_20.0x.jpg`.

### Custom Parameters

```bash
python merge_mif_images.py \
    --input-folder "your_image_folder" \
    --reference-image "reference_image.jpg" \
    --dapi-channel b \
    --motion translation \
    --output-dir merged_output
```

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input-folder` | `ColorDeck_test image` | Folder path containing images to process |
| `--reference-image` | `1_Spleen_DAPI_Lamin B1_RF 775_下_20.0x.jpg` | Reference image filename (inside input folder) |
| `--dapi-channel` | `b` | DAPI channel selection: `b` (blue), `g` (green), `r` (red) |
| `--motion` | `translation` | Registration motion model: `translation`, `euclidean`, `affine` |
| `--output-dir` | `merged_output` | Output directory name |

---

## Output

The program creates a timestamped output directory inside the input folder with the following structure:

```
merged_output_YYYYMMDD_HHMMSS/
├── aligned_images/           # Registered images
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── registration_previews/    # Registration quality previews
│   ├── image1_registration_check.png
│   ├── image2_registration_check.png
│   └── ...
├── merged_image.png          # Final merged image
├── input_and_merged_overview.png  # Input images + merged result overview
└── transform_info.txt        # Transformation matrices and registration scores
```

### Output Files Description

| File | Description |
|------|-------------|
| `aligned_images/` | Contains all registered images |
| `registration_previews/` | Registration quality visualization (Red = reference DAPI, Green = aligned DAPI, Yellow = overlap) |
| `merged_image.png` | Result of pixel-wise maximum merging of all images |
| `input_and_merged_overview.png` | Grid overview that combines all original input fluorescence images and the final merged image |
| `transform_info.txt` | Records registration method, score, and transformation matrix for each image |

---

## Algorithm

### Registration Pipeline

```
Reference Image ──┐
                  ├── Extract DAPI Channel ── Normalize ── Gaussian Blur ── ECC Registration ── Transform Alignment
Moving Image ─────┘
```

### ECC Algorithm

ECC (Enhanced Correlation Coefficient) is an image registration algorithm based on brightness consistency with the following advantages:

- Invariance to illumination changes
- High registration accuracy
- Support for various transformation models

The algorithm iteratively optimizes the transformation matrix to maximize the correlation coefficient between the moving image and the reference image.

### Phase Correlation

When the ECC algorithm fails (translation model only), the program automatically switches to phase correlation:

- Translation estimation in the frequency domain
- Fast computation
- Good robustness to noise

---

## Notes

1. **Image Size**: Non-reference images are automatically matched to the reference size before registration, using center crop first and resizing when needed
2. **Reference Image Selection**: Choose an image with clear DAPI signal and clean background as reference
3. **Motion Model Selection**:
   - `translation`: For cases with only translation, fastest
   - `euclidean`: For cases with translation and rotation
   - `affine`: For cases with translation, rotation, scaling, and shearing
4. **Memory Usage**: Processing large images may require significant memory

---

## Supported Image Formats

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- TIFF (`.tif`, `.tiff`)
- BMP (`.bmp`)

---

## License

MIT License
