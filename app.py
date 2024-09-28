import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from main import get_response, get_image  # Ensure these functions are properly defined in main.py
import os
import shutil

# Function to overlay text on image
def overlay_text(original_image_path, overlay_image_path, texts):
    image = Image.open(original_image_path).convert("RGBA")
    txt_layer = Image.new("RGBA", image.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt_layer)

    for text_info in texts:
        text = text_info['text']
        font_size = text_info['font_size']
        font_style = text_info['font_style']
        position = (text_info['x'], text_info['y'])
        text_color = text_info['text_color']
        stroke_width = text_info['stroke_width']
        stroke_color = text_info['stroke_color']

        try:
            font = ImageFont.truetype(font_style, font_size)
        except IOError:
            font = ImageFont.load_default()
            st.warning(f"Font '{font_style}' not found. Using default font.")

        draw.text(
            position,
            text,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color
        )

    combined = Image.alpha_composite(image, txt_layer)
    combined = combined.convert("RGB")  # Convert back to RGB to save in JPEG or PNG
    combined.save(overlay_image_path)
    return overlay_image_path

# Initialize Streamlit session state
if 'image_generated' not in st.session_state:
    st.session_state.image_generated = False
    st.session_state.original_image_path = ""
    st.session_state.current_image_path = ""
    st.session_state.overlay_done = False

# Title of the app
st.title("AI Book Cover Generator")

# Step 1: Generate Book Cover
if not st.session_state.image_generated and not st.session_state.overlay_done:
    # Input field to accept the book summary
    book_description = st.text_area("Enter the Book Description:", height=300)

    # Button to generate the cover prompt and image
    if st.button("Generate Book Cover"):
        if book_description:
            with st.spinner("Generating the book cover image..."):
                # Step 2: Generate the book cover image based on the book description
                get_image(book_description)  # Ensure this saves the image at './gen-img1.png'
                st.session_state.image_generated = True
                st.session_state.original_image_path = './gen-img1.png'
                st.session_state.current_image_path = './gen-img1.png'
                st.success("Book cover image generated successfully!")
        else:
            st.error("Please enter a book description to generate a cover!")

# Step 2: Display Generated Image and Options
if st.session_state.image_generated and not st.session_state.overlay_done:
    st.image(st.session_state.current_image_path, caption="Generated Book Cover", use_column_width=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Regenerate Image"):
            # Reset the state to allow regeneration
            st.session_state.image_generated = False
            st.session_state.image_path = ""
            st.session_state.overlay_done = False
            st.write("Please generate a new image.")

    with col2:
        if st.button("Proceed to Text Overlay"):
            st.session_state.overlay_done = True

# Step 3: Text Overlay Inputs
if st.session_state.overlay_done:
    st.header("Add Text Overlays to Your Book Cover")

    # Function to collect text parameters
    def get_text_inputs(label):
        st.subheader(label)
        text = st.text_input(f"{label} Text:", key=f"{label}_text")
        font_size = st.number_input(f"{label} Font Size:", min_value=10, max_value=200, value=40, key=f"{label}_size")
        font_style = st.selectbox(
            f"{label} Font Style:",
            options=["arial.ttf"],  # Add more font options as needed
            index=0,
            key=f"{label}_style"
        )
        x = st.number_input(f"{label} X Coordinate:", min_value=0, max_value=2000, value=50, key=f"{label}_x")
        y = st.number_input(f"{label} Y Coordinate:", min_value=0, max_value=2000, value=50, key=f"{label}_y")
        text_color = st.color_picker(f"{label} Text Color:", "#FFFFFF", key=f"{label}_color")
        stroke_width = st.number_input(f"{label} Stroke Width:", min_value=0, max_value=10, value=2, key=f"{label}_stroke_width")
        stroke_color = st.color_picker(f"{label} Stroke Color:", "#000000", key=f"{label}_stroke_color")

        # Ensure font path is correct (assuming fonts are in a 'fonts' directory)
        font_path = os.path.join(font_style)
        return {
            "label": label,
            "text": text,
            "font_size": font_size,
            "font_style": font_path,  # Corrected to include directory
            "x": x,
            "y": y,
            "text_color": text_color,
            "stroke_width": stroke_width,
            "stroke_color": stroke_color
        }

    # Collect inputs for Title, Subtitle, Author
    title_info = get_text_inputs("Title")
    subtitle_info = get_text_inputs("Subtitle")
    author_info = get_text_inputs("Author Name")

    # Button to apply overlays
    if st.button("Apply Text Overlays"):
        texts = [title_info, subtitle_info, author_info]

        # Check if at least one text is provided
        if any(text['text'] for text in texts):
            with st.spinner("Applying text overlays..."):
                # Create a copy of the original image for overlaying
                overlay_image_path = 'overlayed_image.jpg'
                shutil.copyfile(st.session_state.original_image_path, overlay_image_path)

                # Apply text overlay on the copied image
                output_image_path = overlay_text(st.session_state.original_image_path, overlay_image_path, texts)
                st.session_state.current_image_path = output_image_path
                st.success("Text overlays applied successfully!")
        else:
            st.error("Please provide at least one text to overlay.")

    # Display the updated image
    if os.path.exists(st.session_state.current_image_path):
        st.image(st.session_state.current_image_path, caption="Book Cover with Text Overlays", use_column_width=True)

        # Option to download the updated image
        with open(st.session_state.current_image_path, "rb") as img_file:
            st.download_button(
                label="Download Updated Image",
                data=img_file,
                file_name="generated_book_cover_with_text.png",
                mime="image/png"
            )
