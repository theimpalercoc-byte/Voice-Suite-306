import os, urllib.request, sys

# Official Hugging Face repositories for LivePortrait and sample voices
MODELS = {
    "weights/appearance_feature_extractor.pth": "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/appearance_feature_extractor.pth",
    "weights/motion_extractor.pth": "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/motion_extractor.pth",
    "weights/spade_generator.pth": "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/spade_generator.pth",
    "weights/warping_spade.pth": "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/warping_spade.pth",
}

def download_progress(count, block_size, total_size):
    percent = int(count * block_size * 100 / total_size)
    mb = (count * block_size) / (1024 * 1024)
    total_mb = total_size / (1024 * 1024)
    sys.stdout.write(f"\r  -> Downloading: [{percent}%] {mb:.1f}MB / {total_mb:.1f}MB")
    sys.stdout.flush()

def ensure_models_downloaded():
    os.makedirs("weights", exist_ok=True)
    os.makedirs("voices", exist_ok=True)

    print("[Model Manager] Checking required AI weights...")
    for local_path, url in MODELS.items():
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
            print(f"  ✓ {local_path} (Ready)")
        else:
            print(f"  ⬇️ Fetching {os.path.basename(local_path)} from Hugging Face...")
            try:
                urllib.request.urlretrieve(url, local_path, reporthook=download_progress)
                print(f"\n  ✓ Successfully saved to {local_path}")
            except Exception as e:
                print(f"\n  ⚠️ Download failed for {local_path}: {e}")
                print("     (App will continue using the high-speed warp fallback)")

if __name__ == "__main__":
    ensure_models_downloaded()
