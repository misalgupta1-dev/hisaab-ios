import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING (Safe Refresh)
def load_data(ttl_val=10):
    try:
        raw_df = conn.read(ttl=ttl_val)
        if raw_df is not None:
            raw_df = raw_df.dropna(how='all')
            raw_df["Amount"] = pd.to_numeric(raw_df["Amount"], errors='coerce').fillna(0)
            raw_df["Date"] = pd.to_datetime(raw_df["Date"], errors='coerce')
            clean_df = raw_df.dropna(subset=['Date'])
            return clean_df[clean_df['Amount'] > 0]
    except Exception:
        return st.session_state.get('df', pd.DataFrame(columns=["Date", "Amount", "Category", "Note"]))
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

if "df" not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# --- SECTION 0: GLOBAL TIME FILTER ---
st.sidebar.header("📅 Time Filters")
use_custom_range = st.sidebar.checkbox("Use Custom Date Range", value=False)

if use_custom_range:
    # Let user pick a specific window
    start_date = st.sidebar.date_input("Start Date", datetime.now().replace(day=1))
    end_date = st.sidebar.date_input("End Date", datetime.now())
    # Filter DF
    filtered_df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
    period_label = f"from {start_date.strftime('%d %b')} to {end_date.strftime('%d %b %Y')}"
else:
    # DEFAULT: Current Month only
    curr_month = datetime.now().month
    curr_year = datetime.now().year
    filtered_df = df[(df['Date'].dt.month == curr_month) & (df['Date'].dt.year == curr_year)]
    period_label = datetime.now().strftime('%B %Y')

# --- TOP METRICS ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not filtered_df.empty:
    st.metric(f"Total Spending ({period_label})", f"₹{filtered_df['Amount'].sum():,.2f}")
else:
    st.warning(f"No transactions found for {period_label}.")

# --- SECTION 1: VISUAL ANALYTICS (Filtered by the selected period) ---
if not filtered_df.empty:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_pie = px.pie(
            filtered_df, values='Amount', names='Category', hole=0.4,
            title=f"Spending Split: {period_label}",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_chart2:
        plot_df = filtered_df.copy()
        plot_df['Note'] = plot_df['Note'].fillna('General').replace('', 'General')
        fig_tree = px.treemap(
            plot_df, path=[px.Constant(period_label), 'Category', 'Note'], 
            values='Amount', color='Category',
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Detailed Item Breakdown"
        )
        st.plotly_chart(fig_tree, use_container_width=True)

# --- SECTION 2: ADD, EDIT & DELETE (Operations always use the full master DF) ---
st.divider()
tab1, tab2, tab3 = st.tabs(["➕ Add New", "✏️ Edit Existing", "🗑️ Delete"])

with tab1:
    with st.form("add_form", clear_on_submit=True):
        a_amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
        a_cat = st.selectbox("Category", CATEGORIES, key="add_cat")
        a_nte = st.text_input("Note")
        a_dte = st.date_input("Date", datetime.now(), key="add_date")
        if st.form_submit_button("Save to Cloud"):
            latest = load_data(ttl_val=0)
            new_row = pd.DataFrame([{"Date": pd.to_datetime(a_dte), "Amount": a_amt, "Category": a_cat, "Note": a_nte}])
            updated = pd.concat([latest, new_row], ignore_index=True)
            conn.update(data=updated)
            st.session_state.df = updated
            st.toast("Saved!")
            time.sleep(1); st.rerun()

with tab2:
    if not df.empty:
        edit_df = df.copy().sort_values(by="Date", ascending=False).reset_index()
        edit_df['Label'] = edit_df['Date'].dt.strftime('%d-%b') + " | " + edit_df['Category'] + " | ₹" + edit_df['Amount'].astype(str)
        target_label = st.selectbox("Select entry to edit:", options=edit_df['Label'].tolist())
        row_to_edit = edit_df[edit_df['Label'] == target_label].iloc[0]
        orig_idx = row_to_edit['index']
        
        with st.form("edit_form"):
            e_amt = st.number_input("New Amount (₹)", value=float(row_to_edit['Amount']))
            e_cat = st.selectbox("New Category", CATEGORIES, index=CATEGORIES.index(row_to_edit['Category']))
            e_nte = st.text_input("New Note", value=str(row_to_edit['Note']))
            e_dte = st.date_input("New Date", value=row_to_edit['Date'])
            if st.form_submit_button("Update Changes"):
                st.session_state.df.at[orig_idx, 'Amount'] = e_amt
                st.session_state.df.at[orig_idx, 'Category'] = e_cat
                st.session_state.df.at[orig_idx, 'Note'] = e_nte
                st.session_state.df.at[orig_idx, 'Date'] = pd.to_datetime(e_dte)
                conn.update(data=st.session_state.df)
                st.toast("✅ Updated!")
                time.sleep(1); st.rerun()

with tab3:
    if not df.empty:
        del_df = df.copy().sort_values(by="Date", ascending=False).reset_index()
        del_df['Label'] = del_df['Date'].dt.strftime('%d-%b') + " | " + del_df['Category'] + " | ₹" + del_df['Amount'].astype(str)
        del_label = st.selectbox("Select entry to delete:", options=del_df['Label'].tolist())
        if st.button("Confirm Delete", type="primary"):
            d_idx = del_df[del_df['Label'] == del_label]['index'].values[0]
            st.session_state.df = df.drop(d_idx).reset_index(drop=True)
            conn.update(data=st.session_state.df)
            st.toast("🗑️ Deleted")
            time.sleep(1); st.rerun()

# --- SECTION 3: HISTORY (Filtered to match charts) ---
st.subheader(f"📜 History for {period_label}")
if not filtered_df.empty:
    disp = filtered_df.copy()
    disp['Date'] = disp['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(disp.sort_values(by="Date", ascending=False), use_container_width=True)
