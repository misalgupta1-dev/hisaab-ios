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
    # CRITICAL FIX: Ensure Date is a datetime object for the .dt accessor to work
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    # Remove any rows where the date couldn't be understood
    df = df.dropna(subset=['Date'])

# --- SIDEBAR: BUDGET SETTINGS ---
st.sidebar.header("⚙️ Budget Settings")
budgets = {}
for cat in CATEGORIES:
    # Defaulting to 10k, user can adjust on the fly
    budgets[cat] = st.sidebar.number_input(f"Limit: {cat}", min_value=0, value=10000, step=500)

# --- SECTION 1: BUDGET TRACKER (PROGRESS BARS) ---
st.subheader("⚠️ Monthly Budget Tracker")
if not df.empty:
    curr_month_str = datetime.now().strftime('%Y-%m')
    this_month_df = df[df['Date'].dt.strftime('%Y-%m') == curr_month_str]
    
    for cat in CATEGORIES:
        spent = this_month_df[this_month_df['Category'] == cat]['Amount'].sum()
        limit = budgets[cat]
        # Prevent division by zero
        percent = min(spent / limit, 1.0) if limit > 0 else 0
        
        # Display progress bar
        st.progress(percent, text=f"{cat}: ₹{spent:,.0f} / ₹{limit:,.0f}")
        if spent > limit:
            st.caption(f"🚨 Over budget in {cat}!")

st.divider()

# --- SECTION 2: MONTHLY CATEGORY COMPARISON ---
st.subheader("📈 Monthly Comparison Table")
if not df.empty:
    compare_df = df.copy()
    compare_df['MonthYear'] = compare_df['Date'].dt.strftime('%b %Y')
    # Pivot table for side-by-side comparison
    pivot_table = compare_df.pivot_table(
        index='Category', 
        columns='MonthYear', 
        values='Amount', 
        aggfunc='sum'
    ).fillna(0)
    # Using 'stretch' to satisfy new Streamlit requirements
    st.dataframe(pivot_table.style.format("₹{:,.0f}"), width='stretch')

# --- SECTION 3: ADD NEW EXPENSE ---
with st.expander("➕ Add New Expense", expanded=False):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_area("Note (Optional)")
        dte =
