import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import time

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. ROBUST DATA LOADING
def load_data(ttl_val=60):
    try:
        # We use a small cache to prevent 500 errors during navigation
        data = conn.read(ttl=ttl_val)
        if data is not None:
            data = data.dropna(how='all')
            if not data.empty:
                data["Amount"] = pd.to_numeric(data["Amount"], errors='coerce').fillna(0)
                data["Date"] = pd.to_datetime(data["Date"], errors='coerce')
                return data.dropna(subset=['Date'])
    except Exception:
        # If 500 error hits, return what we have in state or empty df
        return st.session_state.get('df', pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]))
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

# Initialize data
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# --- SECTION 1: INTERACTIVE TREEMAP ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not df.empty:
    st.subheader("📊 Category Drill-down")
    # Clean data for Plotly
    plot_df = df.copy()
    plot_df['Note'] = plot_df['Note'].fillna('Unlabeled').replace('', 'Unlabeled')
    
    fig = px.treemap(
        plot_df, 
        path=[px.Constant("Total Spend"), 'Category', 'Note'], 
        values='Amount',
        color='Category', # Distinct colors for categories
        color_discrete_sequence=px.colors.qualitative.Safe,
        hover_data=['Amount']
    )
    fig.update_layout(margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No transactions to display yet.")

# --- SECTION 2: ACTIONS (ADD & DELETE) ---
st.divider()
col_add, col_del = st.columns(2)

with col_add:
    with st.expander("➕ Add Expense", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            amt = st.number_input("Amount (₹)", min_value=0.0, step=50.0)
            cat = st.selectbox("Category", CATEGORIES)
            nte = st.text_input("Note")
            dte = st.date_input("Date", datetime.now())
            
            if st.form_submit_button("Save to Cloud"):
                # Step 1: Force a fresh read to ensure no data loss
                latest_df = load_data(ttl_val=0)
                # Step 2: Append
                new_row = pd.DataFrame([{"Date": pd.to_datetime(dte), "Amount": amt, "Category": cat, "Note": nte}])
                updated_df = pd.concat([latest_df, new_row], ignore_index=True)
                # Step 3: Update Cloud
                conn.update(data=updated_df)
                # Step 4: Update Local State & Rerun
                st.session_state.df = updated_df
                st.toast("✅ Transaction Saved!")
                time.sleep(1) # Give API a moment to breathe
                st.rerun()

with col_del:
    with st.expander("🗑️ Delete Expense"):
        if not df.empty:
            df_del = df.copy().reset_index()
            df_del['Label'] = df_del['Date'].dt.strftime('%d-%b') + " | " + df_del['Category'] + " | ₹" + df_del['Amount'].astype(str)
            target_label = st.selectbox("Select to remove:", options=df_del['Label'].tolist())
            
            if st.button("Delete Permanently", type="primary"):
                # Filter out the selected row
                target_idx = df_del[df_del['Label'] == target_label]['index'].values[0]
                new_df = df.drop(target_idx).reset_index(drop=True)
                # Update Cloud & Local
                conn.update(data=new_df)
                st.session_state.df = new_df
                st.toast("🗑️ Entry Removed")
                time.sleep(1)
                st.rerun()

# --- SECTION 3: HISTORY ---
st.subheader("📜 History")
if not df.empty:
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
