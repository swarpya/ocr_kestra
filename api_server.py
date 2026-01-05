from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import PlainTextResponse
import io
import gc
from contextlib import asynccontextmanager
from PIL import Image
import pytesseract
import pypdfium2 as pdfium

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- STARTUP: LOADING AI MODELS ---")
    try:
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        from surya.layout import LayoutPredictor
        from surya.foundation import FoundationPredictor
        
        print("Loading Surya Foundation...")
        foundation_predictor = FoundationPredictor()
        
        print("Loading Surya Detection...")
        models['detection'] = DetectionPredictor()
        
        print("Loading Surya Layout...")
        models['layout'] = LayoutPredictor(foundation_predictor)
        
        print("Loading Surya Recognition...")
        models['recognition'] = RecognitionPredictor(foundation_predictor)
        
        print("--- MODELS LOADED SUCCESSFULLY ---")
    except Exception as e:
        print(f"Error loading models: {e}")
    yield
    print("--- SHUTDOWN ---")

app = FastAPI(lifespan=lifespan)

@app.post("/ocr", response_class=PlainTextResponse)
async def process_document(
    file: UploadFile = File(...),
    engine: str = Form("surya") 
):
    content = await file.read()
    filename = file.filename.lower()
    full_text = ""

    # 1. Load Images (Force RGB)
    try:
        pil_images = []
        if filename.endswith(".pdf"):
            pdf = pdfium.PdfDocument(content)
            for i in range(len(pdf)):
                pil_images.append(pdf[i].render(scale=2.0).to_pil().convert("RGB"))
        else:
            pil_images.append(Image.open(io.BytesIO(content)).convert("RGB"))
    except Exception as e:
        return f"Error reading file: {e}"

    # 2. Process
    if engine == "tesseract":
        for i, img in enumerate(pil_images):
            full_text += f"\n--- Page {i+1} ---\n"
            full_text += pytesseract.image_to_string(img)

    elif engine == "surya":
        layout_predictor = models['layout']
        rec_predictor = models['recognition']
        det_predictor = models['detection']

        for i, image in enumerate(pil_images):
            print(f"--- Processing Page {i+1} ---")
            page_text = ""
            
            # --- ATTEMPT A: SMART LAYOUT (Columns & Diagrams) ---
            try:
                layout_pred = layout_predictor([image])[0]
                bboxes = sorted(layout_pred.bboxes, key=lambda x: x.bbox[1])
                
                # Check if layout found ANYTHING
                if not bboxes:
                    raise Exception("No layout blocks found")

                for box in bboxes:
                    if box.label in ["Picture", "Figure", "Table", "Image"]:
                        page_text += f"\n[DIAGRAM: {box.label}]\n"
                    elif box.label in ["Text", "Title", "Section-header", "List-item", "Caption"]:
                        crop = image.crop((box.bbox[0], box.bbox[1], box.bbox[2], box.bbox[3]))
                        
                        # FIX 1: Pass detector as KEYWORD argument
                        ocr_result = rec_predictor([crop], det_predictor=det_predictor)[0]
                        
                        block_text = " ".join([l.text for l in ocr_result.text_lines])
                        if block_text.strip():
                            page_text += block_text + "\n"
            except Exception as e:
                print(f"Smart mode glitch: {e}")

            # --- ATTEMPT B: THE SAFETY FALLBACK ---
            clean_check = page_text.replace("[DIAGRAM: Picture]", "").replace("[DIAGRAM: Figure]", "").strip()
            
            if len(clean_check) < 10:
                print(f"   -> Page {i+1}: Smart mode output too short. Running Full-Page Scan...")
                
                # FIX 2: Pass detector as KEYWORD argument here too
                ocr_result = rec_predictor([image], det_predictor=det_predictor)[0]
                
                fallback_text = " ".join([l.text for l in ocr_result.text_lines])
                
                if "[DIAGRAM:" in page_text:
                    full_text += f"\n--- Page {i+1} ---\n{page_text}\n{fallback_text}"
                else:
                    full_text += f"\n--- Page {i+1} ---\n{fallback_text}"
            else:
                full_text += f"\n--- Page {i+1} ---\n{page_text}"

            # Memory cleanup
            del image
            gc.collect()

    return full_text