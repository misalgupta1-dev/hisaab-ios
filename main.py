import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING (Force refresh every time)
df = conn.read(ttl=0)

# Helper function to clean data
def clean_data(data):
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        data["Amount"] = pd.to_numeric(data["Amount"], errors='coerce').fillna(0)
        data["Date"] = pd.to_datetime(data["Date"], errors='coerce')
        data = data.dropna(subset=['Date'])
        return data[data['Amount'] > 0]
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

df = clean_data(df)

# --- TOP METRICS ---
if not df.empty:
    total_spent = df['Amount'].sum()
    st.metric("Total Household Spending", f"₹{total_spent:,.2f}")

# --- SECTION 1: VISUAL DASHBOARD ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not df.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig_pie = px.pie(df, values='Amount', names='Category', hole=0.4,
                         title="Spending Split by Category",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        plot_df = df.copy()
        plot_df['Note'] = plot_df['Note'].fillna('General')
        fig_tree = px.treemap(plot_df, path=['Category', 'Note'], values='Amount',
                              title="Detailed Breakdown",
                              color='Amount', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("No transactions found. Add one below!")

# --- SECTION 2: ADD NEW EXPENSE (THE FIX IS HERE) ---
st.divider()
with st.expander("➕ Add New Expense", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_input("Note (Optional)")
        dte = st.date_input("Date", datetime.now())
        
        if st.form_submit_button("Save Transaction"):
            # RE-READ DATA IMMEDIATELY to avoid overwriting other people's/previous entries
            current_df = conn.read(ttl=0)
            
            new_row = pd.DataFrame([{
                "Date": dte.strftime("%Y-%m-%d"), 
                "Amount": amt, 
                "Category": cat, 
                "Note": nte
            }])
            
            # Combine current sheet data with the new row
            updated_df = pd.concat([current_df, new_row], ignore_index=True)
            
            # Push back to Google Sheets
            conn.update(data=updated_df)
            
            st.success(f"Saved ₹{amt} for {cat}!")
            st.rerun()

# --- SECTION 3: RECENT HISTORY ---
st.subheader("📜 Recent History")
if not df.empty:
    # Formatting for display
    display_df = df.copy()
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(display_df.sort_values(by="Date", ascending=False), use_container_width=True)
