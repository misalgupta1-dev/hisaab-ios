import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING LOGIC (With 1-minute safety cache)
def load_data(ttl_seconds=60):
    try:
        data = conn.read(ttl=ttl_seconds)
        if data is not None and not data.empty:
            data = data.dropna(how='all')
            data["Amount"] = pd.to_numeric(data["Amount"], errors='coerce').fillna(0)
            data["Date"] = pd.to_datetime(data["Date"], errors='coerce')
            return data.dropna(subset=['Date'])
    except Exception as e:
        st.error(f"Google API is busy. Wait 30 seconds and refresh. Error: {e}")
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

# Use Session State to keep data between internal reruns
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# --- SECTION 1: DYNAMIC VISUALS ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not df.empty:
    st.subheader("📊 Interactive Spending Breakdown")
    plot_df = df.copy()
    plot_df['Note'] = plot_df['Note'].fillna('General')
    
    # TREEMAP with Drill-down capability
    fig_tree = px.treemap(
        plot_df, 
        path=[px.Constant("All Spending"), 'Category', 'Note'], 
        values='Amount',
        color='Amount', 
        color_continuous_scale='RdYlGn_r',
        template='plotly_white'
    )
    st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("No data found. Add an expense below!")

# --- SECTION 2: ADD & DELETE ---
st.divider()
col_add, col_del = st.columns(2)

with col_add:
    with st.expander("➕ Add New Expense", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
            cat = st.selectbox("Category", CATEGORIES)
            nte = st.text_input("Note")
            dte = st.date_input("Date", datetime.now())
            
            if st.form_submit_button("Save to Cloud"):
                # Fetch absolute latest to prevent overwrite
                fresh_df = load_data(ttl_seconds=0) 
                new_row = pd.DataFrame([{"Date": pd.to_datetime(dte), "Amount": amt, "Category": cat, "Note": nte}])
                updated_df = pd.concat([fresh_df, new_row], ignore_index=True)
                
                conn.update(data=updated_df)
                st.session_state.df = updated_df # Sync local state
                st.success("Saved!")
                st.rerun()

with col_del:
    with st.expander("🗑️ Delete Expense"):
        if not df.empty:
            df_del = df.copy().reset_index()
            df_del['Label'] = df_del['Date'].dt.strftime('%d-%b') + " | " + df_del['Category'] + " | ₹" + df_del['Amount'].astype(str)
            
            selected_label = st.selectbox("Pick to remove:", options=df_del['Label'].tolist())
            
            if st.button("Delete Permanently", type="primary"):
                # Remove the row
                row_idx = df_del[df_del['Label'] == selected_label]['index'].values[0]
                new_df = df.drop(row_idx).reset_index(drop=True)
                
                conn.update(data=new_df)
                st.session_state.df = new_df # Sync local state
                st.warning("Deleted!")
                st.rerun()

# --- SECTION 3: HISTORY ---
st.subheader("📜 History")
if not df.empty:
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
