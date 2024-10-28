import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from main import get_response, get_image
import os
import shutil
import tempfile
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets API client using credentials from secrets
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
    }
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# Access the Google Sheet
def get_google_sheet(client, spreadsheet_url):
    sheet = client.open_by_url(spreadsheet_url).sheet1  # Opens the first sheet
    return sheet

# Read the password from the first cell
def read_password_from_sheet(sheet):
    password = sheet.cell(1, 1).value  # Reads the first cell (A1)
    return password

# Update the password in the first cell
def update_password_in_sheet(sheet, new_password):
    sheet.update_cell(1, 1, new_password)  # Updates the first cell (A1) with the new password

# Initialize gspread client and access the sheet
client = get_gspread_client()
sheet = get_google_sheet(client, st.secrets["gemini"]["spreadsheet"])
PASSWORD = read_password_from_sheet(sheet)

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'password' not in st.session_state:
    st.session_state['password'] = PASSWORD
if 'reset_mode' not in st.session_state:
    st.session_state['reset_mode'] = False

# Function to check password
def check_password(password):
    return password == st.session_state['password']

# Password reset function
def reset_password(new_password, confirm_password):
    if new_password != confirm_password:
        st.error("Passwords do not match!")
    else:
        st.session_state['password'] = new_password
        update_password_in_sheet(sheet, new_password)
        st.session_state['reset_mode'] = False
        st.success("Password reset successfully!")

# Authentication block
if not st.session_state['authenticated']:
    st.title("Login to AI Book Cover Generator")

    password_input = st.text_input("Enter Password", type="password")
    
    if st.button("Login"):
        if check_password(password_input):
            st.session_state['authenticated'] = True
            st.success("Login successful!")
        else:
            st.error("Incorrect password!")

    if st.button("Reset Password?"):
        st.session_state['reset_mode'] = True

# Reset password block
if st.session_state['reset_mode']:
    st.title("Reset Password")

    old_password = st.text_input("Enter Old Password", type="password")
    new_password = st.text_input("Enter New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    if st.button("Reset Password"):
        if old_password == st.session_state['password']:
            reset_password(new_password, confirm_password)
        else:
            st.error("Incorrect old password!")
    
    if st.button("Back to Login"):
        st.session_state['reset_mode'] = False

if st.session_state['authenticated'] and not st.session_state['reset_mode']:
    # Function to overlay text and image on image with shadow effect
    def overlay_text_and_image(original_image_path, overlay_image_path, texts, overlay_image_data=None, image_options=None):
        image = Image.open(original_image_path).convert("RGBA")
        txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
    
        # Add text overlays
        for text_info in texts:
            text = text_info['text']
            font_size = text_info['font_size']
            font_style = text_info['font_style']
            position = (text_info['x'], text_info['y'])
            text_color = text_info['text_color']
            stroke_width = text_info['stroke_width']
            stroke_color = text_info['stroke_color']
            shadow_color = text_info.get('shadow_color', None)  # Shadow color
            shadow_offset = text_info.get('shadow_offset', (0, 0))  # Shadow offset
    
            try:
                font = ImageFont.truetype(font_style, font_size)
            except IOError:
                font = ImageFont.load_default()
                st.warning(f"Font '{font_style}' not found. Using default font.")
    
            # Handle multiline text
            lines = text.split('\n')
            x, y = position
            for line in lines:
                # Draw shadow first (if shadow is enabled)
                if shadow_color and shadow_offset != (0, 0):
                    shadow_x, shadow_y = shadow_offset
                    draw.text(
                        (x + shadow_x, y + shadow_y),
                        line,
                        font=font,
                        fill=shadow_color
                    )
    
                # Draw main text
                draw.text(
                    (x, y),
                    line,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_color
                )
                try:
                    line_height = font.getbbox('A')[3] + 5  # Approximate line height
                except AttributeError:
                    line_height = font.getsize('A')[1] + 5
                y += line_height
    
        combined = Image.alpha_composite(image, txt_layer)
    
        # Overlay the uploaded image if available
        if overlay_image_data and image_options:
            overlay_img = Image.open(overlay_image_data).convert("RGBA")
            # Resize the overlay image to the desired dimensions
            overlay_img = overlay_img.resize((image_options['width'], image_options['height']))
            # Paste the overlay image at the specified position
            combined.paste(overlay_img, (image_options['x'], image_options['y']), overlay_img)
    
        combined = combined.convert("RGB")  # Convert back to RGB to save in JPEG or PNG
        combined.save(overlay_image_path)
        return overlay_image_path
    # Title of the app
    st.title("AI Book Cover Generator")

    if 'images_generated' not in st.session_state:
        st.session_state.images_generated = False
        st.session_state.original_image_paths = []
        st.session_state.selected_image_path = ""
        st.session_state.overlay_done = False
    
    # Step 1: Generate Book Cover
    if not st.session_state.images_generated and not st.session_state.overlay_done:
        book_description = st.text_area("Enter the Book Description:", height=300)
        aspect_ratios = ['1:1', '9:16', '16:9', '4:3', '3:4']
    
        # Selectbox with default value
        selected_ratio = st.selectbox("Select Aspect Ratio", options=aspect_ratios, index=1)
    
        # Button to generate the cover prompt and image
        if st.button("Generate Book Covers"):
            if book_description:
                with st.spinner("Generating book cover images..."):
                    try:
                        image_paths = get_image(book_description, selected_ratio, number_of_images=4)
                        st.session_state.images_generated = True
                        st.session_state.original_image_paths = image_paths
                        st.session_state.selected_image_path = image_paths[0]  # Default selection
                        st.success("Book cover images generated successfully!")
                    except Exception as e:
                        error_message = str(e).lower()
                        if "safety filter" in error_message or "prohibited words" in error_message:
                            st.error("The prompt violates the content policy. Please modify your description and try again.")
                        else:
                            st.error("An error occurred while generating the images. Please try again.")
            else:
                st.error("Please enter a book description to generate covers!")
    
    # Step 2: Display Generated Images and Selection
    if st.session_state.images_generated and not st.session_state.overlay_done:
        st.subheader("Select an Image to Proceed with Text Overlay")
        
        # Display images in a grid (2x2)
        cols = st.columns(2)
        for idx, img_path in enumerate(st.session_state.original_image_paths):
            with cols[idx % 2]:
                if os.path.exists(img_path):
                    image = Image.open(img_path)
                    st.image(image, use_column_width=True, caption=f"Image {idx+1}")
                    # Radio button for selection
                    if st.button(f"Select Image {idx+1}", key=f"select_{idx}"):
                        st.session_state.selected_image_path = img_path
                        st.success(f"Image {idx+1} selected for text overlay.")
    
        st.image(st.session_state.selected_image_path, caption="Selected Image for Overlay", use_column_width=True)
    
        col1, col2 = st.columns(2)
    
        with col1:
            if st.button("Regenerate Images"):
                # Clean up generated images
                for path in st.session_state.original_image_paths:
                    if os.path.exists(path):
                        os.remove(path)
                st.session_state.images_generated = False
                st.session_state.original_image_paths = []
                st.session_state.selected_image_path = ""
                st.session_state.overlay_done = False
                st.write("Please generate new images.")
    
        with col2:
            if st.button("Proceed to Text Overlay"):
                st.session_state.overlay_done = True
    
    # Step 3: Text and Image Overlay Inputs
    if st.session_state.overlay_done:
        st.header("Add Text Overlays to Your Book Cover")
    
        # Function to collect text parameters
        def get_text_inputs(label):
            st.subheader(label)
            text = st.text_area(f"{label} Text:", key=f"{label}_text", height=100)
            font_size = st.number_input(f"{label} Font Size:", min_value=10, max_value=200, value=40, key=f"{label}_size")
            
            # File uploader for font
            uploaded_font = st.file_uploader(f"{label} Font (Optional TTF File):", type=["ttf"], key=f"{label}_font")
            
            x = st.number_input(f"{label} X Coordinate:", min_value=0, max_value=2000, value=50, key=f"{label}_x")
            y = st.number_input(f"{label} Y Coordinate:", min_value=0, max_value=2000, value=50, key=f"{label}_y")
            text_color = st.color_picker(f"{label} Text Color:", "#FFFFFF", key=f"{label}_color")
            stroke_width = st.number_input(f"{label} Stroke Width:", min_value=0, max_value=10, value=2, key=f"{label}_stroke_width")
            stroke_color = st.color_picker(f"{label} Stroke Color:", "#000000", key=f"{label}_stroke_color")
            
            # Shadow effect inputs
            shadow_color = st.color_picker(f"{label} Shadow Color:", "#000000", key=f"{label}_shadow_color")
            shadow_x = st.number_input(f"{label} Shadow X Offset:", min_value=-2000, max_value=2000, value=2, key=f"{label}_shadow_x")
            shadow_y = st.number_input(f"{label} Shadow Y Offset:", min_value=-2000, max_value=2000, value=2, key=f"{label}_shadow_y")
            
            # Set the font path if a file is uploaded, otherwise use a default font
            font_path = None
            if uploaded_font is not None:
                font_path = os.path.join("fonts/", uploaded_font.name)
                with open(font_path, "wb") as f:
                    f.write(uploaded_font.getbuffer())
            else:
                font_path = "fonts/arial.ttf"  # Default to Arial or a system font
            
            return {
                "label": label,
                "text": text,
                "font_size": font_size,
                "font_style": font_path,
                "x": x,
                "y": y,
                "text_color": text_color,
                "stroke_width": stroke_width,
                "stroke_color": stroke_color,
                "shadow_color": shadow_color,
                "shadow_offset": (shadow_x, shadow_y)
            }
    
    
        # Collect inputs for Title, Subtitle, Author
        title_info = get_text_inputs("Title")
        subtitle_info = get_text_inputs("Subtitle")
        author_info = get_text_inputs("Author Name")
    
        # Image overlay section
        st.subheader("Overlay an Image")
    
        uploaded_image = st.file_uploader("Choose an image to overlay", type=["jpg", "png", "jpeg"], key="overlay_image")
    
        if uploaded_image:
            st.image(uploaded_image, caption="Uploaded Image for Overlay", use_column_width=True)
    
            overlay_image_width = st.number_input("Overlay Image Width", min_value=10, max_value=2000, value=200, key="overlay_width")
            overlay_image_height = st.number_input("Overlay Image Height", min_value=10, max_value=2000, value=200, key="overlay_height")
            overlay_image_x = st.number_input("Overlay Image X Position", min_value=0, max_value=2000, value=50, key="overlay_x")
            overlay_image_y = st.number_input("Overlay Image Y Position", min_value=0, max_value=2000, value=50, key="overlay_y")
    
            image_options = {
                'width': overlay_image_width,
                'height': overlay_image_height,
                'x': overlay_image_x,
                'y': overlay_image_y
            }
        else:
            image_options = None
    
        # Button to apply overlays
        if st.button("Apply Text and Image Overlays"):
            texts = [title_info, subtitle_info, author_info]
    
            if any(text['text'].strip() for text in texts) or uploaded_image:
                with st.spinner("Applying overlays..."):
                    try:
                        # Use the selected image
                        overlay_image_path = 'overlayed_image.jpg'
                        shutil.copyfile(st.session_state.selected_image_path, overlay_image_path)
                        output_image_path = overlay_text_and_image(
                            st.session_state.selected_image_path,
                            overlay_image_path,
                            texts,
                            uploaded_image,
                            image_options
                        )
                        st.session_state.current_image_path = output_image_path
                        st.success("Overlays applied successfully!")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
            else:
                st.error("Please provide either text or an image to overlay.")
    
        if 'current_image_path' in st.session_state and os.path.exists(st.session_state.current_image_path):
            st.image(st.session_state.current_image_path, caption="Book Cover with Overlays", use_column_width=True)
    
            with open(st.session_state.current_image_path, "rb") as img_file:
                st.download_button(
                    label="Download Updated Image",
                    data=img_file,
                    file_name="generated_book_cover_with_text_and_image.png",
                    mime="image/png"
                )
