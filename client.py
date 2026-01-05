import requests
import os
import time

# URL of your Docker API
# In Codespaces, use localhost if running the script inside the terminal.
API_URL = "http://localhost:8000/ocr"

# Folder containing your documents
INPUT_FOLDER = "./documents_to_scan"
OUTPUT_FOLDER = "./ocr_results"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(INPUT_FOLDER, exist_ok=True)

def scan_file(filename):
    file_path = os.path.join(INPUT_FOLDER, filename)

    print(f"🚀 Sending {filename} to API...")
    start_time = time.time()

    try:
        with open(file_path, "rb") as f:
            # Payload: 'file' is the binary, 'engine' is the text field
            files = {"file": (filename, f, "application/pdf")}
            data = {"engine": "surya"} 

            response = requests.post(API_URL, files=files, data=data)

        duration = time.time() - start_time

        if response.status_code == 200:
            print(f"✅ Success! ({duration:.2f}s)")
            return response.text
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return None

if __name__ == "__main__":
    # 1. Check if input folder is empty
    files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))]

    if not files:
        print(f"⚠️  No files found in '{INPUT_FOLDER}'. Please put some PDFs/Images there!")
    else:
        print(f"Found {len(files)} documents. Starting batch job...\n")

        for filename in files:
            text = scan_file(filename)

            if text:
                # Save the result to a text file
                output_filename = f"{filename}.txt"
                with open(os.path.join(OUTPUT_FOLDER, output_filename), "w") as f:
                    f.write(text)
                print(f"📝 Saved result to {output_filename}\n")