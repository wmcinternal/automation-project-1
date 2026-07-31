import os
import json
from openai import OpenAI
import base64
import fitz
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat


GITHUB_API_TOKEN=os.getenv("GITHUB_API_TOKEN")

def convert_pdf_to_base64_images(pdf_path: str, max_pages: int = 3) -> list[str]:
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return []
    
    images=[]
    try:
        doc=fitz.open(pdf_path)
        for page_no in range(min(len(doc), max_pages)):
            page=doc.load_page(page_no)
            pix=page.get_pixmap(dpi=300)
            img=pix.tobytes("jpeg")
            b64_img=base64.b64encode(img).decode('utf-8')
            images.append(b64_img)
        doc.close()
    except Exception as e:
        print(f"⚠️ Error rendering PDF images: {e}")

    return images


def get_relevant_context(docling_doc, target_class: str) -> str:
    """Finds and merges only the sections/pages where target_class and minimum investment appear."""
    relevant_texts = []
    
    for item, level in docling_doc.iterate_items():
        if hasattr(item, "text") and item.text:
            text = item.text.lower()
            # Dynamic filter: Grab text nodes containing investment terms or target share class
            if any(k in text for k in ["minimum", "initial", "subsequent", "subscription"]) or target_class.lower() in text:
                relevant_texts.append(item.text)
                
    return "\n".join(relevant_texts)[:6000] # Dynamic & relevant payload!


def extract_table_crop(pdf_path: str) -> list[str]:
    if not os.path.exists:
        return []
    
    table_crops = []
    try:
        doc = fitz.open(pdf_path)
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        
        for table in result.document.tables:
            if table.prov:
                prov = table.prov[0]
                page_no = prov.page_no - 1
                bbox = prov.bbox
                
                page = doc.load_page(page_no)
                rect = fitz.Rect(bbox.l, bbox.t, bbox.r, bbox.b)
                
                pix = page.get_pixmap(dpi=300, clip=rect)
                img_bytes = pix.tobytes("png")
                b64_img = base64.b64encode(img_bytes).decode('utf-8')
                table_crops.append(b64_img)
        doc.close()
    except Exception as e:
        print(f"⚠️ Error cropping tables: {e}")
        
    return table_crops


def extract_markdown_with_docling(pdf_path: str) -> str:

    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return ""
    try:
        pipeline_options=PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode=TableFormerMode.ACCURATE
        
        converter=DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        result=converter.convert(pdf_path)
        for node, level in result.document.iterate_items():
            if hasattr(node, "text") and node.text:
                print(f"[{node.label}] {node.text}")

        for i, table in enumerate(result.document.tables):
            df=table.export_to_dataframe()
            print(f"\n--- TABLE {i} DATAFRAME ---")
            print(df)

        markdown_text=result.document.export_to_markdown()
        print("✅ Docling reconstruction complete.")
        return markdown_text
    
    except Exception as e:
        print(f"⚠️ Error during Docling processing: {e}")
        return ""



def extract_with_ai(markdown_context: str, images: list[str], target_class: str, target_currency: str) -> dict:

    if not GITHUB_API_TOKEN:
        print("❌ Error: GITHUB_API_TOKEN not found in OS environment variables!")
        return None

    print("🔌 Connecting to Github api token using OS Environment Variable...")

    client=OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_API_TOKEN,
    )

    '''
    target_class="A2"
    target_currency="NZD"

     = f"""
    You are promptan SFC compliance auditor performing high-precision visual table extraction.

    TARGET AUDIT PARAMETERS:
    - Target Share Class: {target_class}
    - Target Currency: {target_currency}

    STRICT EXTRACTION RULES:
    1. **Identify Share Class Headers**:
       - Locate the "Minimum Investment" / "Minimum Subscription Amount" section.
       - Distinguish between different Share Classes (e.g., 'A' vs 'C').
       - DO NOT mix up numbers belonging to Class C with Class A!
    
    2. **Class-Specific Row Matching**:
       - For Target Class "{target_class}" AND Target Currency "{target_currency}":
         - "Min Int Amt": Extract the initial investment figure specifically mapped to Class {target_class}.
         - "Min Sub Amt": Extract the additional/subsequent investment figure specifically mapped to Class {target_class}.
    
    3. **Missing/N/A Handling**:
       - If there is NO separate "Additional" or "Subsequent" column/amount specified for Class {target_class}, set "Min Sub Amt" to 0.0.
       - NEVER assign another share class's Initial amount (like Class C's 1,200,000) as Class {target_class}'s Additional amount!
    
    NUMBER FORMATTING:
    - Convert multipliers like "1.5 million" -> 1500000.0.
    - Convert figures like "1,000" -> 1000.0 or "3,000" -> 3000.0.
    - Strip commas, symbols (*, †), and currency codes.

    Respond ONLY in valid raw JSON:
    {{
        "{target_class}": {{
            "Min Int Amt": 0.0,
            "Min Sub Amt": 0.0
        }}
    }}
    """
    '''
    '''
    prompt = f"""
    You are an SFC compliance auditor performing layout-agnostic investment metric extraction.

    DOCUMENT TEXT & VISUAL CONTEXT:
    {markdown_context}

    TARGET SEARCH PARAMETERS:
    - Target Class: {target_class}
    - Target Currency: {target_currency}

    FLEXIBLE PARSING RULES:
    1. Identify the metric block or table containing investment amounts.
    2. Determine the structural orientation:
       - Header/Key-Value List: Headers may say "Minimum initial investment", "Initial", "First subscription", etc.
       - Tabular/Grid: "Initial" and "Subsequent/Additional" may appear as column or row headers.
    3. Match the entry that corresponds to Target Class "{target_class}" AND Target Currency "{target_currency}".
    4. Extract two values:
       - Initial investment amount -> map to "Min Int Amt"
       - Subsequent/Additional investment amount -> map to "Min Sub Amt" (If non-existent or "N/A", return 0.0)

    NUMBER FORMATTING:
    - Multipliers: "1.5 million" -> 1500000.0
    - Figures: "10,000" -> 10000.0, "1,000" -> 1000.0
    - Clean currency codes (USD, HKD, RMB), symbols ($, ¥), and footnotes (*, †).

    Respond ONLY in valid raw JSON format:
    {{
        "{target_class} {target_currency}": {{
            "Min Int Amt": 0.0,
            "Min Sub Amt": 0.0
        }}
    }}
    """
    '''


    
    prompt = f"""
    You are an SFC compliance auditor performing layout-agnostic investment metric extraction.

    DOCUMENT TEXT & VISUAL CONTEXT:
    {markdown_context}

    TARGET SEARCH PARAMETERS:
    - Target Class: {target_class}
    - Target Currency: {target_currency}

    UNIVERSAL EXTRACTION RULES:
    1. LOCATE & MAP VALUES:
       - Find the row or explicit text corresponding to "{target_currency}".
       - Cross-reference with the column or text assigned to Class "{target_class}".
       - MAP "Min Int Amt": Extract the "initial" or "first" investment figure.
       - MAP "Min Sub Amt": Extract the "additional" or "subsequent" investment figure.
    2. STRICT NUMBER BOUNDARY RULE:
       - Adjacent numbers on the same line (e.g. "CAD1,500 1,000,000") represent SEPARATE columns.
       - NEVER merge or blend digits from neighboring share class columns (e.g. "1,500" and "1,000,000" must NEVER become "1,500,000").
       - Extract ONLY the single discrete figure in the Target Class column.

    3. MULTIPLIERS & ZERO-HANDLING:
       - Convert multipliers ONLY if explicitly printed as words (e.g. "1.5 million" -> 1500000.0).
       - If "Additional" or "Subsequent" is blank, "-", or "N/A", return 0.0 for "Min Sub Amt".

    4. STRICT CURRENCY BOUNDARY RULE:
       - The investment figure you extract MUST explicitly belong to "{target_currency}".
       - If the investment figure is explicitly labeled with a DIFFERENT currency (e.g., "US$500" or "All Class A shares: US$500") and no separate "{target_currency}" tier is provided, YOU MUST RETURN 0.0. 
       - DO NOT assume a base USD amount automatically applies to GBP, EUR, or HKD.


    ALL CURRENCY UNDER CLASS IS SEEN AS UNDER THIS CLASS, DONT ASSIGN CURRENCY TO CLASS/INITAL/SUBSEQUENT BY PROXIMITY
    Respond ONLY in valid raw JSON format:
    {{
        "{target_class}": {{
            "Min Int Amt": 0.0,
            "Min Sub Amt": 0.0
        }}
    }}
    """

    

    
    content=[{"type":"text", "text":prompt}]
    for image in images:
        content.append(
            {
                "type":"image_url",
                "image_url": {"url":f"data:image/png;base64,{image}",
                "detail": "high" }
            }
        )


    print("🔌 Sending Docling context to GitHub AI Agent...")

    try:
        response=client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {   "role": "user",
                    "content": content
                }
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )

            
        raw_response=response.choices[0].message.content
        print("\n✅ Success! Secure Response Received from Github Models:\n")
        parsed_data = json.loads(raw_response)
        return parsed_data

    except Exception as e:
        print(f"\n❌Connection Failed: {e}")
        return None

'''
def extract_safe_pdf_text(pdf_path: str, max_pages: int = 3) -> str:
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return ""
    
    extracted_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text(
                    layout=True,
                    x_tolerance=2,
                    y_tolerance=3
                )
                if page_text:
                    extracted_text += page_text + "\n--- PAGE BREAK ---\n"
    except Exception as e:
        print(f"⚠️ Error reading PDF layout: {e}")
    
    return extracted_text
'''


if __name__=="__main__":

    TARGET_PDF="AMO918_KPS.pdf"
    TARGET_CLASS="A"
    TARGET_CURRENCY="USD"


    print(f"🚀 Starting extraction pipeline for: {TARGET_PDF}")

    pdf_images = convert_pdf_to_base64_images(TARGET_PDF, max_pages=1)
    table_crops=extract_table_crop(TARGET_PDF)
    payload_images=table_crops if table_crops else pdf_images
    docling=extract_markdown_with_docling(TARGET_PDF)
    truncated_context = docling[:5000] if docling else ""

    if docling:

        metrics=extract_with_ai(
            markdown_context=truncated_context,
            images=payload_images,
            target_class=TARGET_CLASS,
            target_currency=TARGET_CURRENCY
        )
        if metrics:
            print("\n✅ Final Extracted Metrics (JSON):")
            print(json.dumps(metrics, indent=4))

'''
    images=convert_pdf_to_base64_images(TARGET_PDF, max_pages=5)
    if images:
        metrics = extract_with_ai(images)

        if metrics:
            print("\n✅ Final Extracted Metrics (JSON):")
            print(json.dumps(metrics, indent=4))
'''