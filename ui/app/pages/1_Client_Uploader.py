# ui/app/pages/1_Client_Uploader.py
import streamlit as st

st.set_page_config(page_title="Upload Ticket", layout="wide")

# --- Security Guard ---
# Check if the user is logged in
if 'token' not in st.session_state:
    st.warning("Please log in to access this page.")
    st.stop() # Stop further execution of the page

# --- Page Content ---
st.title("📄 Upload Your Receipt")
st.write("Use the uploader below to submit a photo of your ticket or receipt.")

uploaded_file = st.file_uploader(
    "Choose a receipt image...", 
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    # Display the uploaded image
    st.image(uploaded_file, caption="Uploaded Receipt.", use_column_width=True)
    
    if st.button("Process Receipt"):
        with st.spinner("Processing your receipt... This may take a moment."):
            # --- Placeholder for API call ---
            # In the future, we will send this file to our OCR service API
            # For example:
            # files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            # response = requests.post("http://ocr-service:8000/scan", files=files)
            # if response.status_code == 200:
            #     st.success("Receipt processed successfully!")
            # else:
            #     st.error("Failed to process the receipt.")
            
            # Mock success for now
            import time
            time.sleep(2)
            st.success("Receipt processed successfully!")