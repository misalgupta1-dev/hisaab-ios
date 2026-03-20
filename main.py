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

# --- TOP METRICS ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not df.empty:
    st.metric("Total Spending", f"₹{df['Amount'].sum():,.2f}")

# --- SECTION 1: VISUAL ANALYTICS (PIE + TREEMAP) ---
if not df.empty:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # PIE CHART: Showing Percentages
        fig_pie = px.pie(
            df, values='Amount', names='Category', hole=0.4,
            title="Spending Split (%)",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_chart2:
        # TREEMAP: Drill-down Capability
        plot_df = df.copy()
        plot_df['Note'] = plot_df['Note'].fillna('General').replace('', 'General')
        fig_tree = px.treemap(
            plot_df, path=[px.Constant("All Expenses"), 'Category', 'Note'], 
            values='Amount', color='Category',
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Detailed Item Breakdown"
        )
        st.plotly_chart(fig_tree, use_container_width=True)

# --- SECTION 2: ADD, EDIT & DELETE ---
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
        # Create a labeled list for selection
        edit_df = df.copy().reset_index()
        edit_df['Label'] = edit_df['Date'].dt.strftime('%d-%b') + " | " + edit_df['Category'] + " | ₹" + edit_df['Amount'].astype(str)
        target_label = st.selectbox("Select entry to edit:", options=edit_df['Label'].tolist())
        
        # Get the current values of the selected row
        row_to_edit = edit_df[edit_df['Label'] == target_label].iloc[0]
        orig_idx = row_to_edit['index']
        
        with st.form("edit_form"):
            e_amt = st.number_input("New Amount (₹)", value=float(row_to_edit['Amount']))
            e_cat = st.selectbox("New Category", CATEGORIES, index=CATEGORIES.index(row_to_edit['Category']))
            e_nte = st.text_input("New Note", value=str(row_to_edit['Note']))
            e_dte = st.date_input("New Date", value=row_to_edit['Date'])
            
            if st.form_submit_button("Update Changes"):
                # Update the specific row in our local dataframe
                st.session_state.df.at[orig_idx, 'Amount'] = e_amt
                st.session_state.df.at[orig_idx, 'Category'] = e_cat
                st.session_state.df.at[orig_idx, 'Note'] = e_nte
                st.session_state.df.at[orig_idx, 'Date'] = pd.to_datetime(e_dte)
                
                # Push the whole thing back to Cloud
                conn.update(data=st.session_state.df)
                st.toast("✅ Updated!")
                time.sleep(1); st.rerun()

with tab3:
    if not df.empty:
        del_df = df.copy().reset_index()
        del_df['Label'] = del_df['Date'].dt.strftime('%d-%b') + " | " + del_df['Category'] + " | ₹" + del_df['Amount'].astype(str)
        del_label = st.selectbox("Select entry to delete:", options=del_df['Label'].tolist())
        if st.button("Confirm Delete", type="primary"):
            d_idx = del_df[del_df['Label'] == del_label]['index'].values[0]
            st.session_state.df = df.drop(d_idx).reset_index(drop=True)
            conn.update(data=st.session_state.df)
            st.toast("🗑️ Deleted")
            time.sleep(1); st.rerun()

# --- SECTION 3: HISTORY ---
st.subheader("📜 History")
if not df.empty:
    disp = df.copy()
    disp['Date'] = disp['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(disp.sort_values(by="Date", ascending=False), use_container_width=True)
