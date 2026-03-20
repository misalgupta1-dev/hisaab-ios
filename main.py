import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

# Set page configuration
st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab & Budgeting")

# 1. INITIALIZE CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DEFINE HOUSEHOLD CATEGORIES
CATEGORIES = [
    "Housing & Utilities", 
    "Food & Dining", 
    "Transportation & Travel", 
    "Health & Wellness", 
    "Shopping & Lifestyle", 
    "Education & Career", 
    "Financial & Legal", 
    "Other/Misc"
]

# 3. LOAD & CLEAN DATA
df = conn.read()

if not df.empty:
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=['Date'])

# --- SIDEBAR: BUDGET SETTINGS ---
st.sidebar.header("⚙️ Budget Settings")
budgets = {}
for cat in CATEGORIES:
    budgets[cat] = st.sidebar.number_input(f"Limit: {cat}", min_value=0, value=10000, step=500)

# --- SECTION 1: BUDGET TRACKER ---
st.subheader("⚠️ Monthly Budget Tracker")
if not df.empty:
    curr_month_str = datetime.now().strftime('%Y-%m')
    this_month_df = df[df['Date'].dt.strftime('%Y-%m') == curr_month_str]
    
    for cat in CATEGORIES:
        spent = this_month_df[this_month_df['Category'] == cat]['Amount'].sum()
        limit = budgets[cat]
        percent = min(spent / limit, 1.0) if limit > 0 else 0
        
        st.progress(percent, text=f"{cat}: ₹{spent:,.0f} / ₹{limit:,.0f}")
        if spent > limit:
            st.caption(f"🚨 Over budget in {cat}!")

st.divider()

# --- SECTION 2: MONTHLY CATEGORY COMPARISON ---
st.subheader("📈 Monthly Comparison Table")
if not df.empty:
    compare_df = df.copy()
    compare_df['MonthYear'] = compare_df['Date'].dt.strftime('%b %Y')
    pivot_table = compare_df.pivot_table(
        index='Category', 
        columns='MonthYear', 
        values='Amount', 
        aggfunc='sum'
    ).fillna(0)
    st.dataframe(pivot_table.style.format("₹{:,.0f}"), width='stretch')

# --- SECTION 3: ADD NEW EXPENSE ---
with st.expander("➕ Add New Expense", expanded=False):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_area("Note (Optional)")
        dte = st.date_input("Date", datetime.now())
        
        if st.form_submit_button("Save to Google Sheets"):
            new_row = pd.DataFrame([{
                "Date": dte.strftime("%Y-%m-%d"), 
                "Amount": amt, 
                "Category": cat, 
                "Note": nte
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Transaction Saved!")
            st.rerun()

# --- SECTION 4: SEARCH & HISTORY ---
st.subheader("🔍 Search & Filter")
search_query = st.text_input("Search by Note", placeholder="e.g. Rent, Swiggy...")

filtered_df = df.copy()
if search_query and not filtered_df.empty:
    filtered_df = filtered_df[filtered_df['Note'].str.contains(search_query, case=False, na=False)]

if not filtered_df.empty:
    st.dataframe(filtered_df.sort_values(by="Date", ascending=False), width='stretch')

# --- SECTION 5: PDF GENERATOR (FIXED SYNTAX) ---
def create_pdf(dataframe, budget_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, "Household Hisaab Monthly Report", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # FIXED LINE 115: Added closing parenthesis
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(95, 10, "Category", border=1)
    pdf.cell(95, 10, "Total Spent", border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "", 12)
    current_m = datetime.now().strftime('%Y-%m')
    dataframe['Date'] = pd.to_datetime(dataframe['Date'])
    m_df = dataframe[dataframe['Date'].dt.strftime('%Y-%m') == current_m]
    
    for category in CATEGORIES:
        total = m_df[m_df['Category'] == category]['Amount'].sum()
        pdf.cell(95, 10, category, border=1)
        pdf.cell(95, 10, f"Rs. {total:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
        
    return bytes(pdf.output())

st.divider()
st.subheader("📋 Export Data")
if st.button("Generate PDF Report"):
    try:
        pdf_bytes = create_pdf(df, budgets)
        st.download_button(
            label="📩 Download PDF Report",
            data=pdf_bytes,
            file_name=f"Hisaab_Report_{datetime.now().strftime('%b_%Y')}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Could not generate PDF: {e}")

# --- SECTION 6: DELETE ENTRY ---
with st.expander("🗑️ Delete an Entry"):
    if not df.empty:
        delete_options = df.copy()
        delete_options['Display'] = (
            delete_options['Date'].dt.strftime('%Y-%m-%d') + 
            " | ₹" + delete_options['Amount'].astype(str) + 
            " | " + delete_options['Note'].astype(str)
        )
        to_del = st.selectbox("Select entry to remove:", options=delete_options['Display'].tolist())
        
        if st.button("Confirm Delete", type="primary"):
            target_idx = delete_options[delete_options['Display'] == to_del].index[0]
            final_df = df.drop(target_idx)
            conn.update(data=final_df)
            st.rerun()
