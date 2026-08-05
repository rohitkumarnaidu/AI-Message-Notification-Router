import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="AI Message Router", layout="wide", page_icon="📲")

st.title("📲 AI Message Notification Router")
st.markdown("Enterprise-grade multimodal WhatsApp notification router with deterministic safety guardrails.")

output_file = "output.csv"
messages_file = "dataset/messages.csv"

if os.path.exists(output_file) and os.path.exists(messages_file):
    df_out = pd.read_csv(output_file)
    df_msg = pd.read_csv(messages_file)
    
    # Merge on message_id
    df = pd.merge(df_msg, df_out, on="message_id", how="inner")
    
    st.subheader("Message Routing Decisions")
    
    # Action Filters
    action = st.radio("Filter by Action:", ["All", "notify", "digest", "mute"], horizontal=True)
    if action != "All":
        df = df[df["action"] == action]
        
    st.dataframe(df[["message_id", "message_text", "media_type", "action", "message_type", "reason", "confidence"]], use_container_width=True)
    
    st.subheader("Deep Dive Analysis")
    msg_id = st.selectbox("Select a Message ID for Traceability:", df["message_id"].tolist())
    
    if msg_id:
        row = df[df["message_id"] == msg_id].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Routing Action:** `{row['action']}`")
            st.markdown(f"**Category:** `{row['message_type']}`")
            st.markdown(f"**Confidence:** `{row['confidence']}`")
            st.markdown(f"**Evidence IDs:** `{row['evidence_message_ids']}`")
        with col2:
            st.success(f"**Routing Reason:**\n{row['reason']}")
            st.markdown(f"**Original Text:**\n> {row['message_text'] if pd.notna(row['message_text']) else '*No text* (Media Only)'}")
            st.markdown(f"**Media Type:** `{row['media_type'] if pd.notna(row['media_type']) else 'None'}`")
            if pd.notna(row['media_id']):
                st.markdown(f"**Media ID:** `{row['media_id']}`")
else:
    st.warning("Data files not found. Please ensure the pipeline has generated `output.csv`.")
