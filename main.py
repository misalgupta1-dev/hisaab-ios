import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="My Hisaab", page_icon="💰")

st.title("💰 Personal Hisaab (iOS)")

# Create a connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- THE AUTOMATION RECEIVER (Webhook) ---
# This part catches the 'amt' from your iPhone Shortcut URL
query_params = st.query_params

if "amt" in query_params:
    try:
        amount_received = query_params["amt"]
        
        # Read existing data
        df = conn.read()
        
        # Create a new entry
        new_entry = pd.DataFrame([
            {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Amount": amount_received,
                "Note": "Auto-Logged (iOS)"
            }
        ])
        
        # Add new entry to the old data
        updated_df = pd.concat([df, new_entry], ignore_index=True)
        
        # Update the Google Sheet
        conn.update(data=updated_df)
        
        st.success(f"✅ Automatically Logged: ₹{amount_received}")
    except Exception as e:
        st.error(f"Error logging data: {e}")

# --- DISPLAY SECTION ---
st.subheader("Recent Transactions")
try:
    data = conn.read()
    # Sort by date so newest is on top
    st.dataframe(data.iloc[::-1], use_container_width=True)
except:
    st.info("No data found. Your first transaction will appear here!")

# Manual Entry fallback
with st.expander("Add Manually"):
    with st.form("manual_form"):
        m_amt = st.number_input("Amount", min_value=0)
        m_note = st.text_input("Note")
        if st.form_submit_button("Save"):
            df = conn.read()
            new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Amount": m_amt, "Note": m_note}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.rerun()