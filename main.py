import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
from fpdf import FPDF

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION (Using ttl=0 to ensure we always get fresh data)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. CATEGORIES
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

# 3. DATA LOADING
# We set ttl=0 so it doesn't cache old versions of the sheet
df = conn.read(ttl=0)

if df is not None and not df.empty:
    df = df.dropna(how='all')
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.dropna(subset=['Date'])
    # Only keep rows with an actual amount
    df = df[df['Amount'] > 0]

# --- SIDEBAR: BUDGET SETTINGS ---
st.sidebar.header("⚙️ Monthly Limits")
budgets = {cat: st.sidebar.number_input(f"{cat}", min_value=0, value=10000) for cat in CATEGORIES}

# --- SECTION 1: VISUAL DASHBOARD ---
st.subheader("📊 Spending Distribution")
if df is not None and len(df) > 0:
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(df, values='Amount', names='Category', hole=0.4,
                         title="Total Spending Split",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        # Treemap needs at least one 'Note' to look good; filling empty notes with 'Other'
        plot_df = df.copy()
        plot_df['Note'] = plot_df['Note'].fillna('Uncategorized')
        fig_tree = px.treemap(plot_df, path=['Category', 'Note'], values='Amount',
                              title="Spending Breakdown",
                              color='Amount', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("👋 Welcome! Add an expense below to see your charts.")

# --- SECTION 2: BUDGET & TRENDS ---
st.divider()
c_a, c_b = st.columns(2)

with c_a:
    st.subheader("⚠️ Budget vs Actual")
    if df is not None and not df.empty:
        curr_m = datetime.now().strftime('%Y-%m')
        m_df = df[df['Date'].dt.strftime('%Y-%m') == curr_m]
        for cat in CATEGORIES:
            spent = m_df[m_df['Category'] == cat]['Amount'].sum()
            limit = budgets[cat]
            percent = min(spent / limit, 1.0) if limit > 0 else 0
            st.progress(percent, text=f"{cat}: ₹{spent:,.0f} / ₹{limit:,.0f}")

with c_b:
    st.subheader("📈 Monthly Trends")
    if df is not None and not df.empty:
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
        nte = st.text_area("Note")
        dte = st.date_input("Date", datetime.now())
        
        if st.form_submit_button("Save Transaction"):
            new_row = pd.DataFrame([{
                "Date": dte.strftime("%Y-%m-%d"), 
                "Amount": amt, 
                "Category": cat, 
                "Note": nte
            }])
            # Combine and update
            final_df = pd.concat([df, new_row], ignore_index=True) if df is not None else new_row
            conn.update(data=final_df)
            st.success("Success! Dashboard updating...")
            # Using st.rerun to force the app to see the updated sheet immediately
            st.rerun()

# --- SECTION 4: HISTORY ---
st.subheader("📜 Recent History")
if df is not None and not df.empty:
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
  
