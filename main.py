import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab & Budgeting")

# Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. CATEGORIES
CATEGORIES = [
    "Housing & Utilities", "Food & Dining", "Transportation & Travel", 
    "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
    "Financial & Legal", "Other/Misc"
]

# Load Data
df = conn.read()

# --- FIX: Ensure Date is actually a datetime object ---
if not df.empty:
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    # Drop rows where date couldn't be parsed
    df = df.dropna(subset=['Date'])

# --- BUDGET SETTINGS (Sidebar) ---
st.sidebar.header("⚙️ Budget Settings")
budgets = {}
for cat in CATEGORIES:
    budgets[cat] = st.sidebar.number_input(f"Limit: {cat}", min_value=0, value=10000, step=500)

# --- BUDGET TRACKER ---
st.subheader("⚠️ Monthly Budget Tracker")
if not df.empty:
    curr_month = datetime.now().strftime('%Y-%m')
    this_month_df = df[df['Date'].dt.strftime('%Y-%m') == curr_month]
    
    for cat in CATEGORIES:
        spent = this_month_df[this_month_df['Category'] == cat]['Amount'].sum()
        limit = budgets[cat]
        percent = min(spent / limit, 1.0) if limit > 0 else 0
        st.progress(percent, text=f"{cat}: ₹{spent:,.0f} / ₹{limit:,.0f}")

# --- COMPARISON TABLE ---
st.subheader("📈 Monthly Comparison")
if not df.empty:
    compare_df = df.copy()
    compare_df['MonthYear'] = compare_df['Date'].dt.strftime('%b %Y')
    pivot_table = compare_df.pivot_table(index='Category', columns='MonthYear', values='Amount', aggfunc='sum').fillna(0)
    st.dataframe(pivot_table.style.format("₹{:,.0f}"), width='stretch')

# --- ADD EXPENSE ---
with st.expander("➕ Add New Expense"):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_area("Note")
        dte = st.date_input("Date", datetime.now())
        if st.form_submit_button("Save"):
            new_row = pd.DataFrame([{"Date": dte.strftime("%Y-%m-%d"), "Amount": amt, "Category": cat, "Note": nte}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.rerun()

# --- RECENT HISTORY ---
st.subheader("📜 Recent History")
if not df.empty:
    st.dataframe(df.sort_values(by="Date", ascending=False), width='stretch')

# --- FIXED PDF EXPORT FUNCTION ---
def create_pdf(dataframe, budget_dict):
    pdf = FPDF()
    pdf.add_page()
    # Using 'helvetica' to avoid the Arial deprecation warning
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, "Household Hisaab Monthly Report", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(95, 10, "Category", border=1)
    pdf.cell(95, 10, "Total Spent (Current Month)", border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 12)
    curr_month = datetime.now().strftime('%Y-%m')
    # Double check date conversion inside the function
    dataframe['Date'] = pd.to_datetime(dataframe['Date'])
    curr_df = dataframe[dataframe['Date'].dt.strftime('%Y-%m') == curr_month]
    
    for cat in CATEGORIES:
        spent = curr_df[curr_df['Category'] == cat]['Amount'].sum()
        pdf.cell(95, 10, cat, border=1)
        pdf.cell(95, 10, f"Rs. {spent:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
        
    return pdf.output()

st.divider()
st.subheader("📋 Export Report")
if st.button("Generate PDF Report"):
    try:
        pdf_data = create_pdf(df, budgets)
        st.download_button(
            label="Download PDF",
            data=pdf_data,
            file_name=f"Hisaab_Report_{datetime.now().strftime('%b_%Y')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
