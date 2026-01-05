from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import io
import gc
from contextlib import asynccontextmanager
from PIL import Image
import pytesseract
import pypdfium2 as pdfium

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- STARTUP: LOADING SURYA MODELS ---")
    try:
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        from surya.layout import LayoutPredictor
        from surya.foundation import FoundationPredictor
        
        foundation_predictor = FoundationPredictor()
        models['detection'] = DetectionPredictor()
        models['layout'] = LayoutPredictor(foundation_predictor)
        models['recognition'] = RecognitionPredictor(foundation_predictor)
        
        print("--- MODELS LOADED SUCCESSFULLY ---")
    except Exception as e:
        print(f"Error loading models: {e}")
    yield
    print("--- SHUTDOWN ---")

app = FastAPI(lifespan=lifespan)

@app.post("/ocr", response_class=JSONResponse)
async def process_document(
    file: UploadFile = File(...),
    engine: str = Form("surya") 
):
    content = await file.read()
    filename = file.filename.lower()
    
    response_data = {"filename": filename, "engine": engine, "pages": []}

    # Load Images
    try:
        pil_images = []
        if filename.endswith(".pdf"):
            pdf = pdfium.PdfDocument(content)
            for i in range(len(pdf)):
                pil_images.append(pdf[i].render(scale=2.0).to_pil().convert("RGB"))
        else:
            pil_images.append(Image.open(io.BytesIO(content)).convert("RGB"))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    if engine == "surya":
        layout_predictor = models['layout']
        rec_predictor = models['recognition']
        det_predictor = models['detection']

        for i, image in enumerate(pil_images):
            print(f"--- Processing Page {i+1} ---")
            page_data = {"page": i+1, "elements": []}
            text_found_counter = 0  # <--- Track how much text we find
            
            try:
                # 1. Detect Layout
                layout_pred = layout_predictor([image])[0]
                bboxes = sorted(layout_pred.bboxes, key=lambda x: x.bbox[1])
                
                if not bboxes:
                    raise Exception("No layout found")

                for box in bboxes:
                    element = {"type": box.label, "content": ""}
                    
                    # Case A: Diagram/Image (Don't OCR content)
                    if box.label in ["Picture", "Figure", "Table", "Image"]:
                        element["content"] = "[DIAGRAM/TABLE DETECTED]"
                    
                    # Case B: Text (and EVERYTHING else to be safe)
                    else:
                        crop = image.crop(box.bbox)
                        ocr_result = rec_predictor([crop], det_predictor=det_predictor)[0]
                        text = " ".join([l.text for l in ocr_result.text_lines])
                        element["content"] = text.strip()
                        text_found_counter += len(text.strip()) # Count chars
                    
                    if element["content"]:
                        page_data["elements"].append(element)

                # --- THE SAFETY NET ---
                # If we found a diagram but almost NO text (less than 50 chars), 
                # it means Layout failed to grab the text blocks.
                if text_found_counter < 50:
                    print(f"   -> Low text detected ({text_found_counter} chars). Running Safety Scan...")
                    
                    # Run standard OCR on the WHOLE page
                    ocr_result = rec_predictor([image], det_predictor=det_predictor)[0]
                    full_page_text = " ".join([l.text for l in ocr_result.text_lines])
                    
                    # Add it as a fallback block
                    page_data["elements"].append({
                        "type": "Safety-Fallback-Text", 
                        "content": full_page_text
                    })

            except Exception as e:
                print(f"Fallback triggered on Page {i+1}: {e}")
                ocr_result = rec_predictor([image], det_predictor=det_predictor)[0]
                full_text = " ".join([l.text for l in ocr_result.text_lines])
                page_data["elements"].append({"type": "Raw-Text", "content": full_text})

            response_data["pages"].append(page_data)
            del image
            gc.collect()

    elif engine == "tesseract":
        for i, img in enumerate(pil_images):
            text = pytesseract.image_to_string(img)
            response_data["pages"].append({
                "page": i+1,
                "elements": [{"type": "Raw-Text", "content": text.strip()}]
            })

    return JSONResponse(content=response_data)