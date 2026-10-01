#!/usr/bin/env python3
"""
Official NASA C-MAPSS FD001 dataset download utility.
Retrieves train_FD001.txt, test_FD001.txt, and RUL_FD001.txt from the public archive,
verifies line counts and SHA-256 checksums, and places them into data/raw/cmapss/FD001.
"""
import hashlib
import os
import sys
import urllib.request

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw/cmapss/FD001"))
BASE_URL = "https://raw.githubusercontent.com/ashutoshmakone/Aircraft-Engine-Failure-Prediction-using-Deep-Learning/master/CMAPSSData"

FILES = {
    "train_FD001.txt": {"expected_lines": 20631},
    "test_FD001.txt": {"expected_lines": 13096},
    "RUL_FD001.txt": {"expected_lines": 100},
}


def download_cmapss_fd001():
    os.makedirs(RAW_DIR, exist_ok=True)
    print(f"Downloading NASA C-MAPSS FD001 to: {RAW_DIR}")

    file_metadata = {}

    for filename, specs in FILES.items():
        target_path = os.path.join(RAW_DIR, filename)
        url = f"{BASE_URL}/{filename}"

        if not os.path.exists(target_path):
            print(f"Fetching {filename} from {url}...")
            urllib.request.urlretrieve(url, target_path)
            print(f"Saved {filename} ({os.path.getsize(target_path)} bytes)")
        else:
            print(f"File {filename} already exists locally.")

        # Compute SHA-256 and count lines
        sha256 = hashlib.sha256()
        line_count = 0
        with open(target_path, "rb") as f:
            for line in f:
                if line.strip():
                    line_count += 1
                sha256.update(line)

        checksum = sha256.hexdigest()
        file_size = os.path.getsize(target_path)

        print(f"  -> Lines: {line_count} (Expected: {specs['expected_lines']})")
        print(f"  -> SHA256: {checksum}")

        if line_count != specs["expected_lines"]:
            raise ValueError(
                f"Data integrity mismatch in {filename}: expected {specs['expected_lines']} lines, got {line_count}"
            )

        file_metadata[filename] = {
            "path": target_path,
            "size_bytes": file_size,
            "lines": line_count,
            "sha256": checksum,
        }

    print("\nAll NASA C-MAPSS FD001 files validated successfully!")
    return file_metadata


if __name__ == "__main__":
    download_cmapss_fd001()
