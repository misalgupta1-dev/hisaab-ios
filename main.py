import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Hisaab", layout="wide")
st.title("🏡 Household Hisaab")

# Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Categories
CATEGORIES = ["Housing & Utilities", "Food & Dining", "Transportation & Travel", 
              "Health & Wellness", "Shopping & Lifestyle", "Education & Career", 
              "Financial & Legal", "Other/Misc"]

# Load Data
df = conn.read()
if not df.empty:
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)

# --- DASHBOARD ---
if not df.empty and df["Amount"].sum() > 0:
    fig = px.pie(df, values='Amount', names='Category', hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# --- ADD EXPENSE ---
with st.expander("➕ Add New Expense", expanded=False):
    with st.form("entry_form", clear_on_submit=True):
        amt = st.number_input("Amount (₹)", min_value=0.0)
        cat = st.selectbox("Category", CATEGORIES)
        nte = st.text_input("Note")
        if st.form_submit_button("Save"):
            new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Amount": amt, "Category": cat, "Note": nte}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.rerun()

# --- DELETE EXPENSE SECTION ---
st.subheader("🗑️ Delete/Manage Expenses")
if not df.empty:
    # We create a list of options for the user to pick which one to delete
    # Formatting it so it's easy to read on a phone
    df_display = df.copy()
    df_display['Selection'] = df_display['Date'].astype(str) + " | ₹" + df_display['Amount'].astype(str) + " | " + df_display['Note']
    
    to_delete = st.selectbox("Select an expense to remove:", options=df_display['Selection'].tolist())
    
    if st.button("Delete Selected Expense", type="primary"):
        # Find the index of the selected row and drop it
        index_to_drop = df_display[df_display['Selection'] == to_delete].index[0]
        updated_df = df.drop(index_to_drop)
        
        # Update Google Sheets
        conn.update(data=updated_df)
        st.success("Deleted successfully!")
        st.rerun()
else:
    st.info("No expenses found to delete.")
