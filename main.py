import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
from fpdf import FPDF

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. CATEGORIES
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

# 3. DATA LOADING & CLEANING
df = conn.read()
if not df.empty:
    # Remove any completely empty rows from the sheet
    df = df.dropna(how='all')
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=['Date', 'Amount'])

# --- SIDEBAR: BUDGET SETTINGS ---
st.sidebar.header("⚙️ Monthly Limits")
budgets = {cat: st.sidebar.number_input(f"{cat}", min_value=0, value=10000) for cat in CATEGORIES}

# --- SECTION 1: VISUAL DASHBOARD ---
st.subheader("📊 Spending Distribution")
if not df.empty:
    curr_m = datetime.now().strftime('%Y-%m')
    # Filter for current month
    m_df = df[df['Date'].dt.strftime('%Y-%m') == curr_m]
    
    # Decide which data to show: Current Month or All Time (if month is empty)
    plot_df = m_df if not m_df.empty else df
    title_suffix = f"({datetime.now().strftime('%B %Y')})" if not m_df.empty else "(All Time)"
    
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(plot_df, values='Amount', names='Category', hole=0.4,
                         title=f"Category Split {title_suffix}",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        fig_tree = px.treemap(plot_df, path=['Category', 'Note'], values='Amount',
                              title=f"Spending Hierarchy {title_suffix}",
                              color='Amount', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("👋 Welcome! Start by adding an expense below to see your charts.")

# --- SECTION 2: BUDGET & TRENDS ---
st.divider()
c_a, c_b = st.columns(2)

with c_a:
    st.subheader("⚠️ Budget vs Actual")
    if not df.empty:
        curr_month_df = df[df['Date'].dt.strftime('%Y-%m') == datetime.now().strftime('%Y-%m')]
        for cat in CATEGORIES:
            spent = curr_month_df[curr_month_df['Category'] == cat]['Amount'].sum()
            limit = budgets[cat]
            percent = min(spent / limit, 1.0) if limit > 0 else 0
            st.progress(percent, text=f"{cat}: ₹{spent:,.0f} / ₹{limit:,.0f}")

with c_b:
    st.subheader("📈 Monthly Trends")
    if not df.empty:
        trend_df = df.copy()
        trend_df['Month'] = trend_df['Date'].dt.strftime('%b %Y')
        pivot = trend_df.pivot_table(index='Category', columns='Month', values='Amount', aggfunc='sum').fillna(0)
        st.dataframe(pivot.style.format("₹{:,.0f}"), use_container_width=True)

# --- SECTION 3: ACTIONS ---
st.divider()
with st.expander("➕ Add New Expense", expanded=True):
    with st.form("entry", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_area("Note (e.g., Grocery, Rent)")
        dte = st.date_input("Date", datetime.now())
        if st.form_submit_button("Save Transaction"):
            new_data = pd.DataFrame([{"Date": dte.strftime("%Y-%m-%d"), "Amount": amt, "Category": cat, "Note": nte}])
            # Append to existing data
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Saved! Refreshing dashboard...")
            st.rerun()

# --- SECTION 4: HISTORY & PDF ---
st.subheader("📜 Recent History")
if not df.empty:
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)

def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, "Household Hisaab Report", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("helvetica", "", 12)
    for cat in CATEGORIES:
        val = dataframe[dataframe['Category'] == cat]['Amount'].sum()
        pdf.cell(95, 10, cat, border=1)
        pdf.cell(95, 10, f"Rs. {val:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

if st.button("Generate PDF Summary"):
    if not df.empty:
        st.download_button("📩 Download PDF", data=create_pdf(df), file_name="Hisaab_Report.pdf", mime="application/pdf")
    else:
        st.error("No data available to export.")
