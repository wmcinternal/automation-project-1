import os
import pdfplumber
# Summon your actual engine core function directly![cite: 6]
from engine import extract_pdf_metrics 

# Define targets for visual inspection
pdf_name = "BLS811_KPS.pdf"
pdf_folder = "webscrap"
target_ccy = "usd"
target_fund = "BlackRock Global Funds - US Flexible Equity Fund" 

pdf_path = os.path.join(pdf_folder, pdf_name)

if not os.path.exists(pdf_path):
    print(f"❌ Target document missing at: {pdf_path}")
    exit()

# 1. Run the engine process in verification mode to print text data to terminal[cite: 6]
print("🤖 Booting backend parser calculations...")
extracted_data = extract_pdf_metrics(pdf_name, target_ccy, target_fund, folder=pdf_folder) #[cite: 6]
print(f"📊 Engine Output Metrics: {extracted_data}\n")

# 2. Draw visual metrics boundaries to cross-inspect engine alignment paths
print("🎨 Rendering alignment debug canvas...")
with pdfplumber.open(pdf_path) as pdf: #[cite: 5]
    page = pdf.pages[0] #[cite: 5]
    
    # Render PDF coordinates to image layout maps[cite: 5]
    img = page.to_image(resolution=150) #[cite: 5]
    
    # Collect table coordinates
    detected_tables = page.find_tables()
    table_bboxes = [t.bbox for t in detected_tables]
    
    # Outline full table containers in high-contrast blue blocks
    if table_bboxes:
        img.draw_rects(table_bboxes, stroke="blue", stroke_width=3, fill=None)
        print(f"   🔹 Visualized {len(table_bboxes)} base table structures (Blue Border).")
    
    # Cross-match words mapping coordinates[cite: 5]
    words = page.extract_words() #[cite: 5]
    target_words_bboxes = []
    
    for w in words: #[cite: 5]
        text_lower = w["text"].lower()
        # Find every element where the engine checks criteria phrases[cite: 6]
        if "min" in text_lower or "invest" in text_lower or "class" in text_lower: #[cite: 6]
            # FIX: Just append the raw dictionary 'w'! It already contains x0, top, x1, bottom[cite: 5]
            target_words_bboxes.append(w) 
            
    # Highlight regulatory filter keywords in green squares
    if target_words_bboxes:
        # FIX: Changed stroke_width from 1.5 to 1 (must be an integer for PIL)[cite: 5]
        img.draw_rects(target_words_bboxes, stroke="green", stroke_width=1) 
        print(f"   🔸 Visualized {len(target_words_bboxes)} target filtering tokens (Green Border).")

    # Save and output verification profile image data blocks[cite: 5]
    output_filename = "debug_engine_verification.png"
    img.save(output_filename, format="PNG") #[cite: 5]
    print(f"\n🚀 Verification Complete! Open '{output_filename}' to inspect logic coordinates.")