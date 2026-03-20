import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. ESTABLISH CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. LOAD DATA INTO SESSION STATE (To prevent "overwriting" bugs)
if "df" not in st.session_state:
    raw_data = conn.read(ttl=0)
    if raw_data is not None and not raw_data.empty:
        raw_data = raw_data.dropna(how='all')
        raw_data["Amount"] = pd.to_numeric(raw_data["Amount"], errors='coerce').fillna(0)
        raw_data["Date"] = pd.to_datetime(raw_data["Date"], errors='coerce')
        st.session_state.df = raw_data.dropna(subset=['Date'])
    else:
        st.session_state.df = pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

df = st.session_state.df

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
        # Pie Chart: Showing everything to ensure visuals always work
        fig_pie = px.pie(df, values='Amount', names='Category', hole=0.4,
                         title="Overall Spending Split",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        # Treemap: Detailed breakdown
        plot_df = df.copy()
        plot_df['Note'] = plot_df['Note'].fillna('General')
        fig_tree = px.treemap(plot_df, path=['Category', 'Note'], values='Amount',
                              title="Items Breakdown",
                              color='Amount', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("📊 Charts will appear here once you log your first expense.")

# --- SECTION 2: ADD NEW EXPENSE ---
st.divider()
with st.expander("➕ Add New Expense", expanded=True):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_input("Note (e.g., Grocery, Rent)")
        dte = st.date_input("Date", datetime.now())
        
        if st.form_submit_button("Save Transaction"):
            # 1. Create the new row
            new_row = pd.DataFrame([{
                "Date": pd.to_datetime(dte), 
                "Amount": amt, 
                "Category": cat, 
                "Note": nte
            }])
            
            # 2. Update local Session State immediately
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            
            # 3. Push the ENTIRE updated dataframe to Google Sheets
            conn.update(data=st.session_state.df)
            
            st.success(f"Successfully added ₹{amt}!")
            st.rerun()

# --- SECTION 3: RECENT HISTORY ---
st.subheader("📜 Recent History")
if not df.empty:
    # Cleanup for display
    display_df = df.copy()
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(display_df.sort_values(by="Date", ascending=False), use_container_width=True)
