import streamlit as st
import pandas as pd
import os
import zipfile
import traceback

# Import the warning-free functions directly from your engine.py
from engine import webscrap_sfc_pdf, extract_pdf_metrics, run_audit_comparison, load_target_data

# Page Configurations
st.set_page_config(page_title="SFC Audit Portal", page_icon="🛡️", layout="wide")

# App Styling & Sidebar
st.sidebar.title("⚙️ Engine Control Panel")
st.sidebar.write("Configure and run your live regulatory audit checks.")
supported_houses = st.sidebar.multiselect(
    "Supported Fund Houses (Phase 1)", 
    ["AllianceBernstein (AB)"], 
    default=["AllianceBernstein (AB)"]
)

st.title("🛡️ SFC Regulatory Compliance Parser & Audit Shield")
st.write("Upload your internal golden dataset to run live scrapes of SFC product disclosures and verify guidelines.")

# Directory Setup
WEBSCRAP_FOLDER = "./webscrap"
os.makedirs(WEBSCRAP_FOLDER, exist_ok=True)

# 1. FILE UPLOAD INTERFACE
uploaded_file = st.file_uploader("📂 Upload Golden Template (Excel)", type=["xlsx"])

if uploaded_file:
    # Save the file temporarily to run the script against it
    input_path = "uploaded_template.xlsx"
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success("✅ Golden sheet uploaded and validated.")
    
    # 2. RUN BUTTON
    if st.button("🚀 Start Live Scraping & Compliance Run"):
        st.subheader("🖥️ Live Execution Logs (SFC Webscraper & Parser)")
        
        # Create a dynamic logging box that mimics a terminal screen
        log_container = st.empty()
        terminal_logs = "💻 Initializing live engine hooks...\n"
        log_container.code(terminal_logs)
        
        try:
            # Load incoming data
            company_data = load_target_data(input_path)
            final_audit_results = []
            
            # Progress bar for visual comfort
            progress_bar = st.progress(0.0)
            total_rows = len(company_data)
            
            for index, row in enumerate(company_data):
                fund_raw = str(row.get("Fund Name", ""))
                ccy_target = str(row.get("Fund Currency", "")).lower()
                ce_number = row.get("SFC Sub-fund CE No.")
                fund_house = str(row.get("Fund House", "")).upper()
                
                # Check if it's an unsupported house (Failsafe Guard)
                is_supported = any(kw in fund_raw.upper() or kw in fund_house for kw in ["AB ", "ALLIANCEBERNSTEIN", "FCP I"])
                
                terminal_logs += f"\n⚙️ Row {index + 1}/{total_rows}: Checking '{fund_raw}'...\n"
                log_container.code(terminal_logs)
                
                # Handle Blank Rows
                if pd.isna(ce_number) or str(ce_number).strip() == "":
                    terminal_logs += "   ⚪ Skipping blank instruction row.\n"
                    log_container.code(terminal_logs)
                    final_audit_results.append({
                        "Matched PDF": "⚪ BLANK ROW",
                        "Management Company": "⚪ BLANK ROW",
                        "Target Fund": fund_raw,
                        "Currency": ccy_target.upper(),
                        "Min Int Amt Check": "⚪ BLANK ROW",
                        "Min Sub Amt Check": "⚪ BLANK ROW",
                        "Dealing Frequency": "⚪ BLANK ROW"
                    })
                    progress_bar.progress((index + 1) / total_rows)
                    continue

                # Handle Unsupported Fund Houses (Protect against formatting crashes!)
                if not is_supported:
                    terminal_logs += f"   ⚠️ Skipped: Non-AB Fund detected. Format support scheduled for Phase 2.\n"
                    log_container.code(terminal_logs)
                    final_audit_results.append({
                        "Matched PDF": "⚠️ FORMAT INACTIVE",
                        "Management Company": f"🔴 PENDING REGULATION ({fund_house})",
                        "Target Fund": fund_raw,
                        "Currency": ccy_target.upper(),
                        "Min Int Amt Check": "⚠️ PARSER UNSUPPORTED (PHASE 2)",
                        "Min Sub Amt Check": "⚠️ PARSER UNSUPPORTED (PHASE 2)",
                        "Dealing Frequency": "⚠️ PARSER UNSUPPORTED (PHASE 2)"
                    })
                    progress_bar.progress((index + 1) / total_rows)
                    continue

                # Run Scraper live
                terminal_logs += f"   🌐 Fetching latest KFS for CE {ce_number} from SFC server...\n"
                log_container.code(terminal_logs)
                
                pdf_path = webscrap_sfc_pdf(ce_number, folder=WEBSCRAP_FOLDER)
                
                if pdf_path:
                    filename_used = os.path.basename(pdf_path)
                    terminal_logs += f"   ✅ Successfully scraped: '{filename_used}'\n"
                else:
                    filename_used = None
                    terminal_logs += f"   ❌ Document not found on SFC index.\n"
                log_container.code(terminal_logs)
                
                # Run Parser
                terminal_logs += "   🧮 Scanning table structures and mapping currency cells...\n"
                log_container.code(terminal_logs)
                
                extracted_metrics = extract_pdf_metrics(filename_used, ccy_target, fund_raw, folder=WEBSCRAP_FOLDER)
                audit_result = run_audit_comparison(row, extracted_metrics, filename_used)
                
                final_audit_results.append(audit_result)
                terminal_logs += f"   ⭐ Audit Complete! Result: {audit_result.get('Min Int Amt Check')}\n"
                log_container.code(terminal_logs)
                
                # Update progress
                progress_bar.progress((index + 1) / total_rows)
            
            # --- WRITE THE REPORT ---
            output_report_path = "QA_Audit_Report.xlsx"
            report_df = pd.DataFrame(final_audit_results)
            report_df.to_excel(output_report_path, index=False)
            
            terminal_logs += "\n🏁 ALL PROCESSES RESOLVED! Packaging file output structures..."
            log_container.code(terminal_logs)
            
            # Create a ZIP file of the webscrap folder for easy verification download
            zip_path = "webscrap_verification_pdfs.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(WEBSCRAP_FOLDER):
                    for file in files:
                        zipf.write(os.path.join(root, file), arcname=file)
            
            st.balloons()
            st.success("🎉 Process Auditing Complete!")
            
            # --- DOWNLOAD PORTAL ---
            st.subheader("📥 Handoff Download Portal")
            col1, col2 = st.columns(2)
            
            with col1:
                with open(output_report_path, "rb") as file:
                    st.download_button(
                        label="📊 Download Audited Spreadsheet (QA_Audit_Report.xlsx)",
                        data=file,
                        file_name="QA_Audit_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
            with col2:
                with open(zip_path, "rb") as file:
                    st.download_button(
                        label="📂 Download Downloaded SFC Sources (.zip)",
                        data=file,
                        file_name="SFC_Source_Documents.zip",
                        mime="application/zip"
                    )
            
            # Live Interactive Data Preview
            st.subheader("👀 Live Match Verification Table")
            st.dataframe(report_df.style.applymap(
                lambda val: 'background-color: #ffcccc' if "FAIL" in str(val) else ('background-color: #d4edda' if "MATCH" in str(val) else ''),
                subset=['Min Int Amt Check', 'Min Sub Amt Check']
            ))
            
        except Exception as system_err:
            st.error(f"💥 Critical Crash: {system_err}")
            st.code(traceback.format_exc())