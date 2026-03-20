import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Hisaab Pro", layout="wide")
st.title("🏡 Household Hisaab Dashboard")

# 1. CONNECTION & REFRESH LOGIC
conn = st.connection("gsheets", type=GSheetsConnection)

# Function to pull fresh data
def get_data():
    data = conn.read(ttl=0)
    if data is not None and not data.empty:
        data = data.dropna(how='all')
        data["Amount"] = pd.to_numeric(data["Amount"], errors='coerce').fillna(0)
        data["Date"] = pd.to_datetime(data["Date"], errors='coerce')
        return data.dropna(subset=['Date'])
    return pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])

# Load fresh data into session state
if "df" not in st.session_state or st.sidebar.button("🔄 Force Refresh Data"):
    st.session_state.df = get_data()

df = st.session_state.df

# --- SECTION 1: DYNAMIC VISUALS ---
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

if not df.empty:
    st.subheader("📊 Interactive Spending Breakdown")
    st.caption("Click on a large square below to 'drill down' into specific transactions.")
    
    # TREEMAP: Set up with Path [Category -> Note] to allow expansion
    plot_df = df.copy()
    plot_df['Note'] = plot_df['Note'].replace('', 'Unspecified').fillna('Unspecified')
    
    fig_tree = px.treemap(
        plot_df, 
        path=[px.Constant("All Spending"), 'Category', 'Note'], 
        values='Amount',
        color='Amount', 
        color_continuous_scale='RdYlGn_r',
        hover_data=['Amount']
    )
    fig_tree.update_traces(root_color="lightgrey")
    st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("Log your first expense below to see the interactive treemap.")

# --- SECTION 2: ADD NEW EXPENSE ---
st.divider()
col_left, col_right = st.columns([1, 1])

with col_left:
    with st.expander("➕ Add New Expense", expanded=True):
        with st.form("entry_form", clear_on_submit=True):
            amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
            cat = st.selectbox("Category", CATEGORIES)
            nte = st.text_input("Note/Description")
            dte = st.date_input("Date", datetime.now())
            
            if st.form_submit_button("Save Transaction"):
                new_row = pd.DataFrame([{"Date": pd.to_datetime(dte), "Amount": amt, "Category": cat, "Note": nte}])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                conn.update(data=st.session_state.df)
                st.success(f"Saved ₹{amt}")
                st.rerun()

# --- SECTION 3: MANAGEMENT (DELETE & CLEANUP) ---
with col_right:
    with st.expander("🗑️ Delete & Cleanup", expanded=False):
        st.write("Select a transaction to remove it forever:")
        if not df.empty:
            # Create a unique string for each row so user knows what they are deleting
            delete_df = df.copy()
            delete_df['ID'] = delete_df.index
            delete_df['Label'] = (
                delete_df['Date'].dt.strftime('%d-%b') + " | " + 
                delete_df['Category'] + " | ₹" + 
                delete_df['Amount'].astype(str) + " (" + 
                delete_df['Note'].fillna('') + ")"
            )
            
            to_delete_label = st.selectbox("Transaction to delete:", options=delete_df['Label'].tolist())
            
            if st.button("Confirm Permanent Delete", type="primary"):
                # Find the index of the selected label
                idx_to_drop = delete_df[delete_df['Label'] == to_delete_label].index[0]
                # Drop from session state
                st.session_state.df = st.session_state.df.drop(idx_to_drop).reset_index(drop=True)
                # Sync with Google Sheets
                conn.update(data=st.session_state.df)
                st.warning("Transaction Deleted.")
                st.rerun()
        else:
            st.write("No data to delete.")

# --- SECTION 4: HISTORY ---
st.subheader("📜 History Log")
if not df.empty:
    display_df = df.copy()
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(display_df.sort_values(by="Date", ascending=False), use_container_width=True)
