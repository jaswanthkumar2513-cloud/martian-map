import os
import requests

def download_pds_file(url, save_path):
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        print(f"File already exists locally at: {save_path}")
        return

    print(f"Starting download from: {url}")
    try:
        # stream=True is critical for large planetary data files
        response = requests.get(url, stream=True, timeout=30)
        
        # Check if the URL is valid and the file exists
        if response.status_code == 200:
            with open(save_path, 'wb') as file:
                # Download in 8KB chunks
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"Success! File saved locally to: {save_path}")
        else:
            print(f"Failed to download. HTTP Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error during download: {e}")

# ==========================================
# 1. MOLA (Elevation Data) Download 
# ==========================================
# Corrected 16 pix/deg MEGDR topography product: megt90n000eb.img
mola_url = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/megt90n000eb.img"
mola_filename = "mola_elevation_megt90n000eb.img"

# ==========================================
# 2. CTX (Image Data) Download
# ==========================================
# Valid CTX EDR product from PDS volume mrox_3835
ctx_url = "https://planetarydata.jpl.nasa.gov/img/data/mro/ctx/mrox_3835/data/N10_066297_1615_XN_18S152W.IMG"
ctx_filename = "ctx_image_N10_066297_1615.IMG"

# Run the pipeline extraction
print("--- Extracting MOLA Elevation Data ---")
download_pds_file(mola_url, mola_filename)

print("\n--- Extracting CTX Visual Data ---")
download_pds_file(ctx_url, ctx_filename)
