import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Hisaab Dashboard", layout="wide")
st.title("📊 Household Hisaab & Analytics")

# Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. HOUSEHOLD CATEGORIES
CATEGORIES = ["Grocery", "Rent/Bills", "Dining Out", "Transport", "Shopping", "Medical", "Entertainment", "Misc"]

# --- RECEIVER (For your Shortcut) ---
query_params = st.query_params
if "amt" in query_params:
    amt = query_params["amt"]
    df = conn.read()
    # Defaulting automated SMS to 'Misc' - you can change this later
    new_data = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Amount": float(amt), "Category": "Misc", "Note": "Auto-Logged"}])
    conn.update(data=pd.concat([df, new_data], ignore_index=True))
    st.toast(f"Logged ₹{amt}")

# --- DATA LOADING ---
df = conn.read()
df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)

# --- DASHBOARD SECTION ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Spending by Category")
    if not df.empty:
        fig = px.pie(df, values='Amount', names='Category', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_patch(fig) # Optimized for mobile
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to show yet.")

with col2:
    st.subheader("Add Expense")
    with st.form("manual_entry"):
        m_amt = st.number_input("Amount (₹)", min_value=0.0)
        m_cat = st.selectbox("Category", CATEGORIES)
        m_note = st.text_input("Note (Optional)")
        if st.form_submit_button("Save Expense"):
            new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Amount": m_amt, "Category": m_cat, "Note": m_note}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.rerun()

# --- RECENT LOGS ---
st.subheader("Transaction History")
st.dataframe(df.iloc[::-1], use_container_width=True)
