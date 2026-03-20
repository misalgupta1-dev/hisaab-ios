import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Household Hisaab", layout="wide")
st.title("🏡 Household Hisaab & Analytics")

# Connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. YOUR SPECIFIC CATEGORIES
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

# Load Data
df = conn.read()
# Ensure numeric columns and date format
if not df.empty:
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date

# --- DASHBOARD SECTION ---
st.subheader("📊 Spending Breakdown")
if not df.empty and df["Amount"].sum() > 0:
    # Create the Pie Chart
    fig = px.pie(df, values='Amount', names='Category', hole=0.5,
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No spending data available yet. Start by adding an expense below!")

st.divider()

# --- INPUT SECTION ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Add New Expense")
    with st.form("expense_form", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        category = st.selectbox("Category", CATEGORIES)
        note = st.text_area("What was this for? (Notes)", placeholder="e.g., March Electricity Bill, Dinner at Wow Momo")
        date_val = st.date_input("Date", datetime.now())
        
        if st.form_submit_button("Save to Hisaab"):
            new_row = pd.DataFrame([{
                "Date": date_val.strftime("%Y-%m-%d"), 
                "Amount": amount, 
                "Category": category, 
                "Note": note
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Entry Saved!")
            st.rerun()

with col2:
    st.subheader("📜 Recent History")
    if not df.empty:
        # Show last 10 transactions
        st.dataframe(df.iloc[::-1].head(10), use_container_width=True)
    else:
        st.write("Your history is empty.")

# --- FULL DATA VIEW ---
if st.checkbox("Show all transactions"):
    st.dataframe(df.iloc[::-1], use_container_width=True)
