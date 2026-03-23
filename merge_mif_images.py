import argparse
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


CHANNEL_MAP = {
    "b": 0,
    "g": 1,
    "r": 2,
}

MOTION_MAP = {
    "translation": cv2.MOTION_TRANSLATION,
    "euclidean": cv2.MOTION_EUCLIDEAN,
    "affine": cv2.MOTION_AFFINE,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align and merge all multiplex immunofluorescence images in a folder using a reference image."
    )
    parser.add_argument(
        "--input-folder",
        default="ColorDeck_test image",
        help="Folder containing the images to align and merge.",
    )
    parser.add_argument(
        "--reference-image",
        default="1_Spleen_DAPI_Lamin B1_RF 775_下_20.0x.jpg",
        help="Filename of the reference image inside the input folder.",
    )
    parser.add_argument(
        "--dapi-channel",
        default="b",
        choices=sorted(CHANNEL_MAP),
        help="RGB channel used as DAPI. Defaults to blue channel.",
    )
    parser.add_argument(
        "--motion",
        default="translation",
        choices=sorted(MOTION_MAP),
        help="Registration model. Translation is safest when the field is the same but slightly shifted.",
    )
    parser.add_argument(
        "--output-dir",
        default="merged_output",
        help="Output folder name inside the input folder. Absolute paths are also supported.",
    )
    return parser.parse_args()


def load_image(path: str) -> np.ndarray:
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Failed to read image: {path}")
    return image


def save_image(path: Path, image: np.ndarray) -> None:
    suffix = path.suffix or ".png"
    success, encoded = cv2.imencode(suffix, image)
    if not success:
        raise OSError(f"Failed to encode image for saving: {path}")
    encoded.tofile(path)


def normalize_for_registration(channel: np.ndarray) -> np.ndarray:
    channel = channel.astype(np.float32)
    if channel.max() == channel.min():
        return np.zeros_like(channel, dtype=np.float32)
    normalized = cv2.normalize(channel, None, 0.0, 1.0, cv2.NORM_MINMAX)
    return cv2.GaussianBlur(normalized, (0, 0), 2.0)


def estimate_transform_ecc(
    fixed: np.ndarray, moving: np.ndarray, motion_type: int
) -> tuple[np.ndarray, float]:
    if motion_type == cv2.MOTION_HOMOGRAPHY:
        warp = np.eye(3, 3, dtype=np.float32)
    elif motion_type == cv2.MOTION_AFFINE:
        warp = np.eye(2, 3, dtype=np.float32)
    else:
        warp = np.eye(2, 3, dtype=np.float32)

    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        300,
        1e-6,
    )
    cc, warp = cv2.findTransformECC(
        fixed,
        moving,
        warp,
        motion_type,
        criteria,
        inputMask=None,
        gaussFiltSize=5,
    )
    return warp, cc


def estimate_transform_phase_correlation(
    fixed: np.ndarray, moving: np.ndarray
) -> tuple[np.ndarray, float]:
    shift, response = cv2.phaseCorrelate(fixed, moving)
    warp = np.array(
        [[1.0, 0.0, shift[0]], [0.0, 1.0, shift[1]]],
        dtype=np.float32,
    )
    return warp, response


def warp_image(image: np.ndarray, warp: np.ndarray, motion_type: int, size: tuple[int, int]) -> np.ndarray:
    flags = cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP
    if motion_type == cv2.MOTION_HOMOGRAPHY:
        return cv2.warpPerspective(
            image,
            warp,
            size,
            flags=flags,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
    return cv2.warpAffine(
        image,
        warp,
        size,
        flags=flags,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def create_registration_preview(fixed: np.ndarray, aligned: np.ndarray) -> np.ndarray:
    fixed_norm = cv2.normalize(fixed, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    aligned_norm = cv2.normalize(aligned, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    zero = np.zeros_like(fixed_norm)
    # Red = reference DAPI, Green = aligned moving DAPI, Yellow = overlap.
    return cv2.merge([zero, aligned_norm, fixed_norm])


def list_image_files(folder: Path) -> list[Path]:
    supported_suffixes = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
    return sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in supported_suffixes
    )


def build_timestamped_output_dir(input_folder: Path, output_dir_arg: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir_arg)

    if output_dir.is_absolute():
        parent = output_dir.parent
        base_name = output_dir.name
    else:
        parent = input_folder
        base_name = output_dir_arg

    return parent / f"{base_name}_{timestamp}"


def main() -> None:
    args = parse_args()
    input_folder = Path(args.input_folder)
    if not input_folder.is_dir():
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    output_dir = build_timestamped_output_dir(input_folder, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_paths = list_image_files(input_folder)
    if not image_paths:
        raise FileNotFoundError(f"No supported image files found in folder: {input_folder}")

    reference_path = input_folder / args.reference_image
    if not reference_path.is_file():
        raise FileNotFoundError(f"Reference image not found: {reference_path}")

    if reference_path not in image_paths:
        image_paths.append(reference_path)
        image_paths.sort()

    reference_image = load_image(str(reference_path))

    channel_idx = CHANNEL_MAP[args.dapi_channel]
    motion_type = MOTION_MAP[args.motion]

    reference_dapi = normalize_for_registration(reference_image[:, :, channel_idx])
    h, w = reference_image.shape[:2]

    aligned_dir = output_dir / "aligned_images"
    preview_dir = output_dir / "registration_previews"
    aligned_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    merged = reference_image.copy()
    merged_path = output_dir / "merged_image.png"
    info_path = output_dir / "transform_info.txt"
    reference_copy_path = aligned_dir / reference_path.name
    save_image(reference_copy_path, reference_image)

    with info_path.open("w", encoding="utf-8") as f:
        f.write(f"input_folder: {input_folder}\n")
        f.write(f"output_dir: {output_dir}\n")
        f.write(f"reference_image: {reference_path.name}\n")
        f.write(f"motion: {args.motion}\n")
        f.write(f"dapi_channel: {args.dapi_channel}\n")
        f.write("\n")
        f.write(f"[{reference_path.name}]\n")
        f.write("method: reference\n")
        f.write("score: 1.0\n")
        f.write("warp_matrix:\n")
        f.write("1.00000000 0.00000000 0.00000000\n")
        f.write("0.00000000 1.00000000 0.00000000\n\n")

        for image_path in image_paths:
            if image_path == reference_path:
                continue

            moving_image = load_image(str(image_path))
            if moving_image.shape != reference_image.shape:
                raise ValueError(
                    f"Input images must have the same size as the reference image, "
                    f"got {moving_image.shape} and {reference_image.shape} for {image_path.name}."
                )

            moving_dapi = normalize_for_registration(moving_image[:, :, channel_idx])

            try:
                warp, score = estimate_transform_ecc(reference_dapi, moving_dapi, motion_type)
                method = "ECC"
            except cv2.error:
                if motion_type != cv2.MOTION_TRANSLATION:
                    raise
                warp, score = estimate_transform_phase_correlation(reference_dapi, moving_dapi)
                method = "phase_correlation"

            aligned_image = warp_image(moving_image, warp, motion_type, (w, h))
            aligned_dapi = warp_image(moving_image[:, :, channel_idx], warp, motion_type, (w, h))
            preview = create_registration_preview(reference_image[:, :, channel_idx], aligned_dapi)

            merged = np.maximum(merged, aligned_image)

            aligned_path = aligned_dir / image_path.name
            preview_path = preview_dir / f"{image_path.stem}_registration_check.png"
            save_image(aligned_path, aligned_image)
            save_image(preview_path, preview)

            f.write(f"[{image_path.name}]\n")
            f.write(f"method: {method}\n")
            f.write(f"score: {score}\n")
            f.write("warp_matrix:\n")
            for row in warp:
                f.write(" ".join(f"{value:.8f}" for value in row) + "\n")
            f.write("\n")

            print(f"Processed image: {image_path.name}")
            print(f"Registration method: {method}")
            print(f"Registration score: {score}")
            print(f"Aligned image: {aligned_path}")
            print(f"Registration preview: {preview_path}")

    save_image(merged_path, merged)
    print(f"Output directory: {output_dir}")
    print(f"Reference image copied to: {reference_copy_path}")
    print(f"Merged image: {merged_path}")
    print(f"Transform info: {info_path}")


if __name__ == "__main__":
    main()
