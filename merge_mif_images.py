import argparse
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
        description="Align and merge two multiplex immunofluorescence images using their shared DAPI channel."
    )
    parser.add_argument("--round1", default="1_round.jpg", help="First-round image path.")
    parser.add_argument("--round2", default="2_round.jpg", help="Second-round image path.")
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
        default="output",
        help="Directory to save the registered and merged images.",
    )
    return parser.parse_args()


def load_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Failed to read image: {path}")
    return image


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
    # Red = round1 DAPI, Green = aligned round2 DAPI, Yellow = overlap.
    return cv2.merge([zero, aligned_norm, fixed_norm])


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    round1 = load_image(args.round1)
    round2 = load_image(args.round2)

    if round1.shape != round2.shape:
        raise ValueError(
            f"Input images must have the same size, got {round1.shape} and {round2.shape}."
        )

    channel_idx = CHANNEL_MAP[args.dapi_channel]
    motion_type = MOTION_MAP[args.motion]

    dapi1 = normalize_for_registration(round1[:, :, channel_idx])
    dapi2 = normalize_for_registration(round2[:, :, channel_idx])

    try:
        warp, score = estimate_transform_ecc(dapi1, dapi2, motion_type)
        method = "ECC"
    except cv2.error:
        if motion_type != cv2.MOTION_TRANSLATION:
            raise
        warp, score = estimate_transform_phase_correlation(dapi1, dapi2)
        method = "phase_correlation"

    h, w = round1.shape[:2]
    aligned_round2 = warp_image(round2, warp, motion_type, (w, h))
    aligned_dapi2 = warp_image(round2[:, :, channel_idx], warp, motion_type, (w, h))

    merged = np.maximum(round1, aligned_round2)
    preview = create_registration_preview(round1[:, :, channel_idx], aligned_dapi2)

    aligned_path = output_dir / "round2_aligned.png"
    merged_path = output_dir / "merged_image.png"
    preview_path = output_dir / "registration_check.png"
    info_path = output_dir / "transform_info.txt"

    cv2.imwrite(str(aligned_path), aligned_round2)
    cv2.imwrite(str(merged_path), merged)
    cv2.imwrite(str(preview_path), preview)

    with info_path.open("w", encoding="utf-8") as f:
        f.write(f"method: {method}\n")
        f.write(f"score: {score}\n")
        f.write(f"motion: {args.motion}\n")
        f.write(f"dapi_channel: {args.dapi_channel}\n")
        f.write("warp_matrix:\n")
        for row in warp:
            f.write(" ".join(f"{value:.8f}" for value in row) + "\n")

    print(f"Registration method: {method}")
    print(f"Registration score: {score}")
    print(f"Aligned round-2 image: {aligned_path}")
    print(f"Merged image: {merged_path}")
    print(f"Registration preview: {preview_path}")
    print(f"Transform info: {info_path}")


if __name__ == "__main__":
    main()
