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

# 2. AGGRESSIVE DATA LOADING
def load_data(ttl_val=10):
    try:
        # Pull data with a short cache to avoid 500 errors
        raw_df = conn.read(ttl=ttl_val)
        if raw_df is not None:
            # Drop rows that are entirely empty
            raw_df = raw_df.dropna(how='all')
            # Fix column types
            raw_df["Amount"] = pd.to_numeric(raw_df["Amount"], errors='coerce').fillna(0)
            raw_df["Date"] = pd.to_datetime(raw_df["Date"], errors='coerce')
            # Final filter: Must have a date and an amount > 0
            clean_df = raw_df.dropna(subset=['Date'])
            return clean_df[clean_df['Amount'] > 0]
    except Exception:
        # Fallback to session state if Google API fails
        return st.session_state.get('df', pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]))
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

# Initialize session state
if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# --- TOP METRICS ---
if not df.empty:
    total = df['Amount'].sum()
    st.metric("Total Monthly Spending", f"₹{total:,.2f}")

# --- SECTION 1: INTERACTIVE TREEMAP (DRILL-DOWN) ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not df.empty:
    st.subheader("📊 Interactive Breakdown")
    st.caption("Tap a category to see specific items.")
    
    plot_df = df.copy()
    plot_df['Note'] = plot_df['Note'].fillna('General').replace('', 'General')
    
    # Path: Root -> Category -> Note
    fig = px.treemap(
        plot_df, 
        path=[px.Constant("All Expenses"), 'Category', 'Note'], 
        values='Amount',
        color='Category',
        color_discrete_sequence=px.colors.qualitative.Pastel,
        hover_data=['Amount']
    )
    fig.update_traces(root_color="lightgrey")
    fig.update_layout(margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No charts yet. Add a transaction below to see your spending split!")

# --- SECTION 2: ADD & DELETE ---
st.divider()
col_a, col_b = st.columns(2)

with col_a:
    with st.expander("➕ Add Expense", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
            cat = st.selectbox("Category", CATEGORIES)
            nte = st.text_input("Note (e.g. Electricity, Dinner)")
            dte = st.date_input("Date", datetime.now())
            
            if st.form_submit_button("Save to Cloud"):
                # Force refresh from cloud before saving
                current_cloud_df = load_data(ttl_val=0)
                new_entry = pd.DataFrame([{"Date": pd.to_datetime(dte), "Amount": amt, "Category": cat, "Note": nte}])
                updated_df = pd.concat([current_cloud_df, new_entry], ignore_index=True)
                
                conn.update(data=updated_df)
                st.session_state.df = updated_df
                st.toast("✅ Saved Successfully!")
                time.sleep(1)
                st.rerun()

with col_b:
    with st.expander("🗑️ Delete Transaction"):
        if not df.empty:
            df_del = df.copy().reset_index()
            df_del['Label'] = df_del['Date'].dt.strftime('%d-%b') + " | " + df_del['Category'] + " | ₹" + df_del['Amount'].astype(str)
            target = st.selectbox("Select entry:", options=df_del['Label'].tolist())
            
            if st.button("Delete Permanently", type="primary"):
                idx = df_del[df_del['Label'] == target]['index'].values[0]
                new_df = df.drop(idx).reset_index(drop=True)
                
                conn.update(data=new_df)
                st.session_state.df = new_df
                st.toast("🗑️ Entry Deleted")
                time.sleep(1)
                st.rerun()

# --- SECTION 3: HISTORY ---
st.subheader("📜 Recent History")
if not df.empty:
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
