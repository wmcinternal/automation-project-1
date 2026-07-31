import os
import re
import time
import random
import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pandas as pd
from rapidfuzz import fuzz
import pdfplumber

print("\n🚀 Booting up Solid Backend MVP (Read -> Compare -> Write Mode)...\n")

def webscrap_sfc_pdf(ce_number, folder="./webscrap"):

    if not ce_number or pd.isna(ce_number):
        return None
    
    os.makedirs(folder, exist_ok=True)

    ce_clean=str(ce_number).strip().upper()
    ce_name=f"{ce_clean}_KPS.pdf"
    ce_path=os.path.join(folder, ce_name)

    if os.path.exists(ce_path):
        print(f"   ⏭️  [Cache Hit] {ce_name} already exists in {folder}.")
        return ce_path

    url_path=f"https://apps.sfc.hk/productlistWeb/searchProduct/getDocListNoDate.do?lang=EN&ceref={ce_clean}&docType=OD"
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        print(f"   🌐 Connecting to SFC index for CE: {ce_clean}...")
        
        time.sleep(random.uniform(1.0, 2.0))
        
        req=urllib.request.Request(url_path, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            html_content=response.read()
        
        soup=BeautifulSoup(html_content, 'html.parser')
        matching_links = []
        for link in soup.find_all('a', href=True):

            onclick_text=link.get('onclick', '')

            if 'getDoc.do' in onclick_text:
                match=re.search(r"window\.location\.href='([^']+)'", onclick_text)

                if match:
                    matching_links.append(match.group(1))
                    


        if len(matching_links) > 0:
            bottom_href=matching_links[-1]

            full_url=urljoin(url_path, bottom_href)

            print(f"   📥 Bottom Link Found! URL: {full_url}")

            time.sleep(random.uniform(1.5, 3.5))

            target_req=urllib.request.Request(full_url, headers=headers)
            with urllib.request.urlopen(target_req, timeout=12) as stream:
                with open(ce_path, 'wb') as out_file:
                    out_file.write(stream.read())

            print(f"   ✅ Saved completely to: {ce_path}")
            return ce_path
    
    except Exception as e:
        
        print(f"   ❌ Network error for CE {ce_clean}: {e}")
        return None





def load_target_data(excel_path):
    try:
        print(f"📂 Loading target instructions from {excel_path}...")
        df=pd.read_excel(excel_path)
        return df.to_dict('records')
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: Could not find '{excel_path}' in this folder!")
        exit()

"""
def find_and_lock_pdf(target_company_name, target_fund_name, folder="."):

    normalized_name = target_fund_name.lower().replace("-", " ").replace("–", " ")
    excel_words = [w.strip() for w in normalized_name.split() if len(w.strip()) > 1]

    skip_fillers = ["usd", "aud", "hkd", "acc", "hedged", "hdg", "fcp", "funds"]
    core_excel_words = [w for w in excel_words if w not in skip_fillers]

    if not core_excel_words:
        return None
    
    company_keyword = target_company_name.split()[0].lower() if target_company_name else ""
    
    for filename in os.listdir(folder):
        if filename.lower().endswith(".pdf"):
            try:
                with pdfplumber.open(os.path.join(folder, filename)) as pdf:
                    flattened_pdf_text = " ".join(pdf.pages[0].extract_text().lower().split())
                    
                    matched_count = sum(1 for word in core_excel_words if word in flattened_pdf_text)
                    match_percentage = matched_count / len(core_excel_words)


                    if company_keyword and (company_keyword in flattened_pdf_text) and (match_percentage>=0.70):
                        return filename
            except:
                continue

    for filename in os.listdir(folder):
        if filename.lower().endswith(".pdf"):
            try:
                with pdfplumber.open(os.path.join(folder, filename)) as pdf:
                    flattened_pdf_text = " ".join(pdf.pages[0].extract_text().lower().split())

                    matched_count = sum(1 for word in core_excel_words if word in flattened_pdf_text)
                    match_percentage = matched_count / len(core_excel_words)

                    if  match_percentage>=0.7:
                        return filename
            except:
                continue

    return None
"""


"""
def extract_pdf_metrics(matched_pdf, target_currency, target_fund, folder="."):

    engine_data = {"Company": "NOT FOUND", "Min Int Amt": 0.0, "Min Sub Amt": 0.0}

    
    if not matched_pdf:
        return engine_data

    search_currency="rmb" if target_currency.lower()=="cny" else target_currency
                                

    flat_fund_local = target_fund.lower().replace("-", " ")
    class_list = ["a2", "aa", "at", "b2", "c2", "i2", "w2", "bt", "ct", "it", "ia", "wt", "a", "b", "c", "i"]
    share_class_target = next((token for token in flat_fund_local.split() if token in class_list), "a")

    class_pattern = rf"\bclass(?:es)?[ \t]+{share_class_target}\b"

    try:
        with pdfplumber.open(os.path.join(folder, matched_pdf)) as pdf:
            pdf_text=pdf.pages[0].extract_text().lower()
            
            lines = pdf_text.split("\n")
            
            for idx, line in enumerate(lines):
                
                if "min. investment" in line or "minimum investment" in line:
                    
                    for lookahead_offset in range(1, 11):
                        if idx + lookahead_offset >= len(lines):
                            break  

                        target_line = lines[idx + lookahead_offset]
                        
                        is_class_match = (
                            "classes a" in target_line or 
                            "class a" in target_line or 
                            (share_class_target == "aa" and "aa" in target_line.replace(",", " ").split())
                        )
                        
                        if is_class_match:
                            found_initial=False
                            
                            for number_offset in range(0, 5):
                                if idx + lookahead_offset + number_offset >= len(lines):
                                    break
                                num_line = lines[idx + lookahead_offset + number_offset]
                                
                                active_currency = search_currency
                                if target_currency not in num_line and "usd" in num_line:
                                    active_currency = "usd"
                                    
                                if active_currency in num_line:
                                    
                                    all_amounts = re.findall(rf"{active_currency}\s*([0-9][\d,.]*)", num_line)
                                    
                                    if all_amounts:
                                        
                                        values = [float(val.replace(",", "")) for val in all_amounts]
                                        
                                        if len(values) >= 2:
                                            engine_data["Min Int Amt"] = values[0]
                                            engine_data["Min Sub Amt"] = values[1]
                                            break
                                            
                                        else:
                                            amount_value = values[0]
                                            if not found_initial and "subsequent" not in num_line and "additional" not in num_line:
                                                engine_data["Min Int Amt"] = amount_value
                                                found_initial = True
                                            elif found_initial or "subsequent" in num_line or "additional" in num_line:
                                                engine_data["Min Sub Amt"] = amount_value
                                                break



                    if engine_data["Min Int Amt"] > 0.0 or "none" in line:
                        break
    
    except Exception as e:
        print(f"⚠️ Error scraping inner text details from {matched_pdf}: {e}")


    return engine_data
"""

def extract_pdf_metrics(matched_pdf, target_currency, target_fund, folder="."):
    engine_data = {"Company": "NOT FOUND", "Min Int Amt": 0.0, "Min Sub Amt": 0.0}

    if not matched_pdf:
        return engine_data

    target_currency = target_currency.strip().lower()
    if target_currency in ["cny", "cnh", "rmb"]:
        search_currencies=["rmb", "cny", "cnh"]
    else:
        search_currencies=[target_currency]
        
    flat_fund_local = target_fund.lower().replace("-", " ")
    class_list = ["a2", "aa", "at", "b2", "c2", "i2", "w2", "bt", "ct", "it", "ia", "wt", "a", "b", "c", "i"]
    share_class_target = next((token for token in flat_fund_local.split() if token in class_list), "a")

    class_pattern = rf"\bclass(?:es)?\s+{share_class_target}\b"

    try:
        with pdfplumber.open(os.path.join(folder, matched_pdf)) as pdf:
            for page in pdf.pages:
                
                tables = page.extract_tables()
                
                for table in tables:
                    is_target_table = False
                    col_idx_initial = 1  # Default column guesses
                    col_idx_additional = 2
                    
                    for row in table:
                        clean_row = [str(cell).lower().replace('\n', ' ') if cell else "" for cell in row]
                        
                        if any("min. invest" in cell or "minimum invest" in cell for cell in clean_row):
                            is_target_table = True
                            
                            for i, cell in enumerate(clean_row):
                                if "initial" in cell:
                                    col_idx_initial = i
                                elif "additional" in cell or "subsequent" in cell:
                                    col_idx_additional = i
                            continue 

                        if is_target_table and len(clean_row) > 0:
                            cell_0 = clean_row[0]
                            
                            if re.search(class_pattern, cell_0):
                                
                                initial_text = clean_row[col_idx_initial] if len(clean_row) > col_idx_initial else ""
                                additional_text = clean_row[col_idx_additional] if len(clean_row) > col_idx_additional else ""
                                
                                def parse_amount(text, preferred_ccy):
                                    if "none" in text and preferred_ccy not in text and "usd" not in text:
                                        return 0.0 # Default to 0 if it says "None"
                                        
                                    active_ccy = preferred_ccy
                                    if active_ccy not in text and "usd" in text:
                                        active_ccy = "usd"
                                        
                                    match = re.search(rf"{active_ccy}\s*([\d,.]+)\s*(million|m)?", text)
                                    if match:
                                        val = float(match.group(1).replace(',', ''))
                                        if match.group(2): # Multiply if it says 'million'
                                            val *= 1000000
                                        return val
                                    return 0.0 # Default to 0 if no number found

                                engine_data["Min Int Amt"] = parse_amount(initial_text, search_currency)
                                engine_data["Min Sub Amt"] = parse_amount(additional_text, search_currency)
                                
                                return engine_data 

    except Exception as e:
        print(f"⚠️ Error scraping table details from {matched_pdf}: {e}")

    return engine_data





def run_audit_comparison(staff_row, engine_data, matched_pdf):

    ce_number = staff_row.get("SFC Sub-fund CE No.")
    staff_house = str(staff_row.get("Fund House", ""))
    fund_name_target = str(staff_row.get("Fund Name", ""))
    currency_target = str(staff_row.get("Fund Currency", "")).upper()
    staff_amt = float(staff_row.get("Min Int Amt (Fund Ccy)", 0.0))
    sub_amt=float(staff_row.get("Min Sub Amt (Fund Ccy)", 0.0))

    if pd.isna(ce_number) or str(ce_number).strip()=="":
        return {
            "Matched PDF": "⚪ BLANK ROW",
            "Management Company": "⚪ BLANK ROW",
            "Target Fund": fund_name_target,
            "Currency": currency_target.upper(),
            "Min Int Amt Check": "⚪ BLANK ROW"
        }


    if matched_pdf:
        house_status=f"🟢 MATCH ({staff_house})"
    else:
        house_status="🔴 NO MATCHING PDF"
    
    if staff_amt == engine_data["Min Int Amt"]:
        amt_status = "🟢 MATCH"
    else:
        amt_status = f"🔴 FAIL (Excel: {staff_amt} | PDF: {engine_data['Min Int Amt']})"

    if sub_amt == engine_data["Min Sub Amt"]:
        sub_status = "🟢 MATCH"
    else:
        sub_status = f"🔴 FAIL (Excel: {sub_amt} | PDF: {engine_data['Min Sub Amt']})"


    return {
        "Matched PDF": matched_pdf,
        "Management Company": house_status,
        "Target Fund": fund_name_target,
        "Currency": currency_target,
        "Min Int Amt Check": amt_status,
        #"Min Sub Amt Check": sub_status
    }


def generate_audit_report(results_list, output_path):
    
    report_df = pd.DataFrame(results_list)
    
    report_df.to_excel(output_path, index=False)
    
    print("\n✅ SUCCESS! Target metrics computed. Report saved to: QA_Audit_Report.xlsx\n")




if __name__ == "__main__":
    company_data = load_target_data("template_golden.xlsx")
    
    final_audit_results = []

    WEBSCRAP_FOLDER="./webscrap"

    for index, row in enumerate(company_data):
        fund_raw = str(row.get("Fund Name", ""))
        company_raw = str(row.get("Fund House", ""))
        ccy_target = str(row.get("Fund Currency", "")).lower()
        
        
        ce_number=row.get("SFC Sub-fund CE No.")
        print(f"⚙️ Running Row {index + 1} Target: {fund_raw} ({ccy_target.upper()})")


        try:

            webscrap_sfc_pdf(ce_number, folder=WEBSCRAP_FOLDER)

            ce_clean=str(ce_number).strip().upper()
            filename_used=f"{ce_clean}_KPS.pdf"

            ce_file=os.path.join(WEBSCRAP_FOLDER, filename_used)

            if not os.path.exists(ce_file):
                filename_used=None

            extracted_metrics = extract_pdf_metrics(filename_used, ccy_target, fund_raw, folder=WEBSCRAP_FOLDER)
            
            audit_result = run_audit_comparison(row, extracted_metrics, filename_used)
            
            final_audit_results.append(audit_result)
            
        except Exception as row_error:
            
            print(f"❌ Error isolated on Row {index + 1}: {row_error}")
            final_audit_results.append({
                "Matched PDF": "EXCEPTION CAUGHT",
                "Management Company": "💥 SCRAPER EXCEPTION",
                "Target Fund": fund_raw,
                "Currency": ccy_target.upper(),
                "Min Int Amt Check": "💥 SCRAPER EXCEPTION",
                "Min Sub Amt Check": "💥 SCRAPER EXCEPTION"
            })

    
    
    
    generate_audit_report(final_audit_results, 'QA_Audit_Report.xlsx')




            



            



