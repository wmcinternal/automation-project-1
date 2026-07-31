import os
import json
import base64
import fitz  # pip install pymupdf
from openai import OpenAI
from pydantic import BaseModel, Field

# 1. Define the desired structure
class ShareClassMetrics(BaseModel):
    min_int_amt: float = Field(description="Minimum Initial Investment Amount")
    min_sub_amt: float = Field(description="Minimum Subsequent or Additional Investment Amount")

class FundMetrics(BaseModel):
    extracted_data: dict[str, ShareClassMetrics]


def pdf_page_to_base64_png(pdf_path: str, page_num: int = 0) -> str:
    """Converts a specific PDF page to a high-resolution PNG base64 string."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    # 300 DPI ensures crisp text for fine financial tables
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    doc.close()
    return base64.b64encode(img_bytes).decode("utf-8")


def extract_with_github_vision(pdf_path: str, target_class: str, target_currency: str) -> str:
    token = os.getenv("GITHUB_API_TOKEN")
    if not token:
        raise ValueError("Please set your GITHUB_TOKEN environment variable.")

    # Render page 1 (where the Quick Facts / Minimum table is) as a PNG image
    print("🖼️ Converting PDF page to high-res PNG image...")
    base64_image = pdf_page_to_base64_png(pdf_path, page_num=0)

    # Initialize OpenAI client pointing to GitHub Models endpoint
    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )

    prompt = f"""
    Analyze the attached image of the financial document page.
    Locate the 'Minimum Investment / Minimum Subscription Amount' table.
    
    Target Share Class: {target_class}
    Target Currency: {target_currency}
    
    RULES:
    1. Look at visual horizontal alignment to match Share Class '{target_class}' and Currency '{target_currency}'.
    2. Extract 'Initial' as min_int_amt.
    3. Extract 'Additional' as min_sub_amt. If marked as empty, '-', 'N/A', or omitted, return 0.0.
    """

    print("🧠 Sending image context to GitHub Models (gpt-4o)...")
    
    # Send image to gpt-4o via GitHub Models
    response = client.chat.completions.create(
        model="gpt-4o",  # Use full gpt-4o on GitHub Models for vision
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": "high"
                        },
                    },
                ],
            }
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Ensure your GITHUB_TOKEN environment variable is set
    # e.g., in Windows CMD: set GITHUB_TOKEN=github_pat_...
    
    result = extract_with_github_vision("Invesco_test.pdf", "C", "CAD")
    print("\n✅ Final Extracted JSON:")
    print(result)