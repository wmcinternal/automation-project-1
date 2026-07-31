import os
import re
import pandas as pd
import numpy as np
import pdfplumber

print("\n🚀 Starting Phase 1: Batch Processing Engine...\n")

excel_data=[]

for filename in sorted(os.listdir('.')):

    if filename.lower().endswith(".pdf"):
        print(f"📂 Scanning document: {filename}...")

        with pdfplumber.open(filename) as pdf:
            pdf_text=pdf.pages[0].extract_text().lower()

        mgco_valid=re.search(r"\s*(management company|manager)[\s::]+(.*)", pdf_text)
        if mgco_valid: 
            raw_mgco=mgco_valid.group(2) 
            raw_mgco=re.sub(r"[\u4e00-\u9fff（）]+", "", raw_mgco)
            raw_mgco=raw_mgco.strip().title()
        else: 
            raw_mgco="NOT FOUND"
        
        
        if "pay monthly or be reinvested" in pdf_text:
            clean_div="C&R"
        elif "all income are reinvested" in pdf_text or "no dividend" in pdf_text:
            clean_div="R"
        else:
            clean_div="UNKNOWN"


        clean_min=0.0

        for line in pdf_text.split("\n"):

            if "usd" in line and ("initial" in line or "million" in line):

                raw_num=re.search(r"usd\s*([0-9][\d,.]*)\s*(million)?" , line)


                if raw_num:
                    clean_min=float(raw_num.group(1).replace(",",""))

                    if raw_num.group(2)=="million":
                        clean_min*=1000000.0
                        break
                

        excel_data.append({
            "Document Name": filename,
            "Management Company": raw_mgco,
            "Dividend Option": clean_div,
            "Min Int Amt": clean_min
        })

print("\n---BATCH EXTRACTION COMPLETE---\n")
print("📝 Packaging all rows into the Master Excel Database...")

dataframe=pd.DataFrame(excel_data)
output_file="master_regulatory.xlsx"

dataframe.to_excel(output_file, index=False, engine="openpyxl")

print(f"✅ SUCCESS! All PDFs combined and saved to: {output_file}\n")



print("\n🔍 STARTING PHASE 2: QUALITY ASSURANCE CHECKER...\n")

staff_filename="master_checking.xlsx"

try:
    print(f"Loading data from {staff_filename}")
    staff_df=pd.read_excel("master_checking.xlsx")
except FileNotFoundError:
    print(f"❌ ERROR: Could not find '{staff_filename}'. Please create it in this folder to run the audit!")
    exit()


print("🔗 Aligning Engine data with Staff data...")
engine_df=dataframe
qa_df=pd.merge(engine_df, staff_df, on="Document Name",suffixes=('_Engine', '_Staff'))


qa_df["Management Company Check"] = np.where(qa_df["Management Company_Engine"].str.strip().str.lower() == qa_df["Management Company_Staff"].str.strip().str.lower(), "", "Staff: " + qa_df["Management Company_Staff"].astype(str) + " | Correct: " + qa_df["Management Company_Engine"].astype(str))
qa_df["Dividend Option Check"] = np.where(qa_df["Dividend Option_Engine"].str.strip().str.lower() == qa_df["Dividend Option_Staff"].str.strip().str.lower(), "", "Staff: " + qa_df["Dividend Option_Staff"].astype(str) + " | Correct: " + qa_df["Dividend Option_Engine"].astype(str))
qa_df["Min Int Amt Check"] = np.where(qa_df["Min Int Amt_Engine"].astype(int) == qa_df["Min Int Amt_Staff"].astype(int), "", "Staff: " + qa_df["Min Int Amt_Staff"].astype(str) + " | Correct: " + qa_df["Min Int Amt_Engine"].astype(str))

print("="*60)
errors_found=False

def log_error(file_name, col_title, staff_ver, corr_ver):
    print(f"Document Name: {file_name}->Column Title: {col_title}")
    print(f"Staff Version: {staff_ver}")
    print(f"Correct Version: {corr_ver}")

for index, row in qa_df.iterrows():

    doc=row["Document Name"]
    if (row["Management Company Check"]!=""):
        log_error(doc, "Management Company", row["Management Company_Staff"], row["Management Company_Engine"])
        errors_found=True
    if (row["Dividend Option Check"]!=""):
        log_error(doc, "Dividend Option", row["Dividend Option_Staff"], row["Dividend Option_Engine"])
        errors_found=True
    if (row["Min Int Amt Check"]!=""):
        log_error(doc, "Min Int Amt", row["Min Int Amt_Staff"], int(row["Min Int Amt_Engine"]))
        errors_found=True



if not errors_found:
    print("🎉 Congratulations! Verification all PASSED!")

print("="*60)