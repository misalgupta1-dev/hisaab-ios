import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import time

# Move page config to the very top to prevent Safari "Double Load"
st.set_page_config(page_title="Hisaab Pro", layout="wide")

# 1. CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. DATA LOADING (Added extra error catching for Mobile Safari)
@st.cache_data(ttl=10) # Using built-in cache for smoother mobile performance
def load_data():
    try:
        raw_df = conn.read(ttl=0) # Get fresh data
        if raw_df is not None and not raw_df.empty:
            raw_df = raw_df.dropna(how='all')
            raw_df["Amount"] = pd.to_numeric(raw_df["Amount"], errors='coerce').fillna(0)
            raw_df["Date"] = pd.to_datetime(raw_df["Date"], errors='coerce')
            return raw_df.dropna(subset=['Date'])
    except Exception as e:
        return None
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

# Use a lighter way to trigger the first load
if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = load_data()

df = st.session_state.df

if df is None:
    st.error("📡 Connection issue. Please refresh the page.")
    st.stop()

st.title("🏡 Household Hisaab")

# --- SECTION 0: GLOBAL TIME FILTER ---
# Moved to sidebar to save vertical space on iPhone
with st.sidebar:
    st.header("📅 Filters")
    use_custom = st.checkbox("Custom Date Range", value=False)
    if use_custom:
        start = st.date_input("From", datetime.now().replace(day=1))
        end = st.date_input("To", datetime.now())
        filtered_df = df[(df['Date'].dt.date >= start) & (df['Date'].dt.date <= end)]
        period_label = f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
    else:
        # Default: This Month
        now = datetime.now()
        filtered_df = df[(df['Date'].dt.month == now.month) & (df['Date'].dt.year == now.year)]
        period_label = now.strftime('%B %Y')

# --- TOP METRICS ---
if not filtered_df.empty:
    st.metric(f"Total spent in {period_label}", f"₹{filtered_df['Amount'].sum():,.0f}")

# --- SECTION 1: VISUALS ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not filtered_df.empty:
    # Use tabs for charts to prevent Safari from crashing on heavy graphics
    c_tab1, c_tab2 = st.tabs(["⭕ Pie Chart", "🟦 Treemap"])
    
    with c_tab1:
        fig_pie = px.pie(filtered_df, values='Amount', names='Category', hole=0.4)
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c_tab2:
        plot_df = filtered_df.copy()
        plot_df['Note'] = plot_df['Note'].fillna('General')
        fig_tree = px.treemap(plot_df, path=[px.Constant(period_label), 'Category', 'Note'], values='Amount')
        st.plotly_chart(fig_tree, use_container_width=True)

# --- SECTION 2: ADD, EDIT, DELETE ---
st.divider()
t1, t2, t3 = st.tabs(["➕ Add", "✏️ Edit", "🗑️ Delete"])

with t1:
    with st.form("add_form", clear_on_submit=True):
        a_amt = st.number_input("Amount", min_value=0.0)
        a_cat = st.selectbox("Category", CATEGORIES)
        a_nte = st.text_input("Note")
        a_dte = st.date_input("Date", datetime.now())
        if st.form_submit_button("Save"):
            new_row = pd.DataFrame([{"Date":pd.to_datetime(a_dte), "Amount":a_amt, "Category":a_cat, "Note":a_nte}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            conn.update(data=st.session_state.df)
            st.toast("Saved!")
            time.sleep(1); st.rerun()

with t2:
    if not df.empty:
        # Show newest transactions first for easier editing
        e_df = df.copy().sort_values("Date", ascending=False).reset_index()
        e_df['Label'] = e_df['Date'].dt.strftime('%d-%b') + " | ₹" + e_df['Amount'].astype(str)
        target = st.selectbox("Select entry:", options=e_df['Label'].tolist())
        row = e_df[e_df['Label'] == target].iloc[0]
        with st.form("edit_form"):
            new_amt = st.number_input("Amount", value=float(row['Amount']))
            new_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(row['Category']))
            new_nte = st.text_input("Note", value=str(row['Note']))
            if st.form_submit_button("Update"):
                idx = row['index']
                st.session_state.df.at[idx, 'Amount'] = new_amt
                st.session_state.df.at[idx, 'Category'] = new_cat
                st.session_state.df.at[idx, 'Note'] = new_nte
                conn.update(data=st.session_state.df)
                st.toast("Updated!"); time.sleep(1); st.rerun()

with t3:
    if not df.empty:
        d_df = df.copy().sort_values("Date", ascending=False).reset_index()
        d_df['Label'] = d_df['Date'].dt.strftime('%d-%b') + " | ₹" + d_df['Amount'].astype(str)
        d_target = st.selectbox("Delete which?", options=d_df['Label'].tolist())
        if st.button("Confirm Delete", type="primary"):
            d_idx = d_df[d_df['Label'] == d_target]['index'].values[0]
            st.session_state.df = df.drop(d_idx).reset_index(drop=True)
            conn.update(data=st.session_state.df)
            st.toast("Deleted"); time.sleep(1); st.rerun()

# --- SECTION 3: HISTORY ---
st.subheader(f"📜 History: {period_label}")
if not filtered_df.empty:
    st.dataframe(filtered_df.sort_values("Date", ascending=False), use_container_width=True)
