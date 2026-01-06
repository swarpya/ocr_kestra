import requests
import os
import json

# --- CONFIG ---
API_URL = "http://localhost:8000/ocr"
INPUT_FOLDER = "./documents_to_scan"
OUTPUT_FOLDER = "./ocr_results"
# ENGINE = "surya"  # surya gives the best JSON structure
ENGINE = "tesseract"
# --------------

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(INPUT_FOLDER, exist_ok=True)

def scan_file(filename):
    file_path = os.path.join(INPUT_FOLDER, filename)
    print(f"🚀 Sending {filename} [{ENGINE}]...")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            data = {"engine": ENGINE}
            response = requests.post(API_URL, files=files, data=data)
        
        if response.status_code == 200:
            return response.json() # Parse JSON response
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return None

# Change this line in client.py
if __name__ == "__main__":
    # Add .pptx, .xlsx, .xls to the list
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.pptx', '.xlsx', '.xls'))]
    if not files:
        print(f"⚠️  No files in {INPUT_FOLDER}")
    else:
        print(f"Found {len(files)} files. Mode: {ENGINE}\n")
        for filename in files:
            result_json = scan_file(filename)
            if result_json:
                out_name = f"{os.path.splitext(filename)[0]}_{ENGINE}.json"
                out_path = os.path.join(OUTPUT_FOLDER, out_name)
                
                with open(out_path, "w") as f:
                    json.dump(result_json, f, indent=4) # Save formatted JSON
                print(f"✅ Saved JSON: {out_name}\n")