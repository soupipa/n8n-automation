from fastapi import FastAPI, UploadFile, File, Body
from fastapi.responses import FileResponse
from extractor import process_pdf
from build_trilingual import main as build_trilingual_json
import json
import httpx
import os
from typing import Any

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/extract")
async def extract_pdf(file: UploadFile = File(...)):
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    output_path = pdf_path.replace(".pdf", ".json")

    result = process_pdf(pdf_path, output_path)

    return result


@app.post("/extract-and-download")
async def extract_and_download(file: UploadFile = File(...)):
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    output_path = pdf_path.replace(".pdf", ".json")

    process_pdf(pdf_path, output_path)

    return FileResponse(
        output_path,
        media_type="application/json",
        filename="guide_2026_structured.json"
    )

@app.post("/save-dictionary")
async def save_dictionary(data: Any = Body(...)):

    # If n8n sends:
    # [
    #   { ...dictionary... }
    # ]
    if isinstance(data, list):

        if len(data) == 1 and isinstance(data[0], dict):
            master_dict = data[0]
        else:
            merged = {}
            for item in data:
                if isinstance(item, dict):
                    merged.update(item)

            master_dict = merged

    # If n8n sends:
    # { ...dictionary... }
    elif isinstance(data, dict):
        master_dict = data

    else:
        return {
            "success": False,
            "error": "Unsupported JSON structure"
        }

    # Save in the format expected by build_trilingual.py
    dictionary_payload = {
        "masterDict": master_dict
    }

    with open(
        "uploads/merged_dictionnaries.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            dictionary_payload,
            f,
            ensure_ascii=False,
            indent=2
        )

    # Build trilingual file
    build_trilingual_json()

    # Return generated JSON
    return FileResponse(
        "uploads/guide_2026_trilingual.json",
        media_type="application/json",
        filename="guide_2026_trilingual.json"
    )


@app.post("/trigger-remote-trilingual")
async def trigger_remote_trilingual():
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(
            "http://YOUR_OTHER_FASTAPI_SERVER:8001/build-trilingual"
        )

    return response.json()