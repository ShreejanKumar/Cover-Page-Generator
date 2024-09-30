import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from main import get_response, get_image
import os
import shutil

# Function to overlay text and image on image
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

        try:
            font = ImageFont.truetype(font_style, font_size)
        except IOError:
            font = ImageFont.load_default()
            st.warning(f"Font '{font_style}' not found. Using default font.")

        # Handle multiline text
        lines = text.split('\n')
        x, y = position
        for line in lines:
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
    book_description = st.text_area("Enter the Book Description:", height=300)
    aspect_ratios = ['1:1', '9:16', '16:9', '4:3', '3:4']

    # Selectbox with default value
    selected_ratio = st.selectbox("Select Aspect Ratio", options=aspect_ratios, index=1)

    # Button to generate the cover prompt and image
    if st.button("Generate Book Cover"):
        if book_description:
            with st.spinner("Generating the book cover image..."):
                try:
                    get_image(book_description, selected_ratio)
                    st.session_state.image_generated = True
                    st.session_state.original_image_path = './gen-img1.png'
                    st.session_state.current_image_path = './gen-img1.png'
                    st.success("Book cover image generated successfully!")
                except Exception as e:
                    error_message = str(e).lower()
                    if "safety filter" in error_message or "prohibited words" in error_message:
                        st.error("The prompt violates the content policy. Please modify your description and try again.")
                    else:
                        st.error("An error occurred while generating the image. Please try again.")
        else:
            st.error("Please enter a book description to generate a cover!")

# Step 2: Display Generated Image and Options
if st.session_state.image_generated and not st.session_state.overlay_done:
    st.image(st.session_state.current_image_path, caption="Generated Book Cover", use_column_width=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Regenerate Image"):
            st.session_state.image_generated = False
            st.session_state.original_image_path = ""
            st.session_state.current_image_path = ""
            st.session_state.overlay_done = False
            st.write("Please generate a new image.")

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
        font_style = st.selectbox(
            f"{label} Font Style:",
            options = ["arial.ttf", "Arialn.ttf", "ArialTh.ttf", "ARIBL0.ttf", "G_ari_bd.ttf", "G_ari_i.ttf", "GEO_AI__.ttf"],
            index=0,
            key=f"{label}_style"
        )
        x = st.number_input(f"{label} X Coordinate:", min_value=0, max_value=2000, value=50, key=f"{label}_x")
        y = st.number_input(f"{label} Y Coordinate:", min_value=0, max_value=2000, value=50, key=f"{label}_y")
        text_color = st.color_picker(f"{label} Text Color:", "#FFFFFF", key=f"{label}_color")
        stroke_width = st.number_input(f"{label} Stroke Width:", min_value=0, max_value=10, value=2, key=f"{label}_stroke_width")
        stroke_color = st.color_picker(f"{label} Stroke Color:", "#000000", key=f"{label}_stroke_color")
        
        font_path = os.path.join("fonts/", font_style)
        return {
            "label": label,
            "text": text,
            "font_size": font_size,
            "font_style": font_path,
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

    # Image overlay section
    st.subheader("Overlay an Image")

    uploaded_image = st.file_uploader("Choose an image to overlay", type=["jpg", "png", "jpeg"])

    if uploaded_image:
        st.image(uploaded_image, caption="Uploaded Image for Overlay", use_column_width=True)

        overlay_image_width = st.number_input("Overlay Image Width", min_value=10, max_value=2000, value=200)
        overlay_image_height = st.number_input("Overlay Image Height", min_value=10, max_value=2000, value=200)
        overlay_image_x = st.number_input("Overlay Image X Position", min_value=0, max_value=2000, value=50)
        overlay_image_y = st.number_input("Overlay Image Y Position", min_value=0, max_value=2000, value=50)

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
                    overlay_image_path = 'overlayed_image.jpg'
                    shutil.copyfile(st.session_state.original_image_path, overlay_image_path)
                    output_image_path = overlay_text_and_image(
                        st.session_state.original_image_path,
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

    if os.path.exists(st.session_state.current_image_path):
        st.image(st.session_state.current_image_path, caption="Book Cover with Overlays", use_column_width=True)

        with open(st.session_state.current_image_path, "rb") as img_file:
            st.download_button(
                label="Download Updated Image",
                data=img_file,
                file_name="generated_book_cover_with_text_and_image.png",
                mime="image/png"
            )
