import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
from fpdf import FPDF
import io

# Set page to wide mode for better dashboard viewing on mobile
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
    # Ensure Amount is numeric
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    # Ensure Date is a datetime object
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    # Remove any rows where the date couldn't be parsed
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

# --- SECTION 3: ADD NEW EXPENSE (FIXED SYNTAX) ---
with st.expander("➕ Add New Expense", expanded=False):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_area("Note (Optional)")
        # FIXED LINE 86:
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

# --- SECTION 5: PDF GENERATOR ---
def create_pdf(dataframe, budget_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, "Household Hisaab Monthly Report", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12
