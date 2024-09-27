import streamlit as st
from main import get_response, get_image

# Title of the app
st.title("AI Book Cover Generator")


# Input field to accept the book summary
book_description = st.text_area("Enter the Book description:", height=300)

# Button to generate the cover prompt and image
if st.button("Generate Book Cover"):
    if book_description:
        # Step 1: Generate the book cover prompt based on the book summary
        # st.write("Analyzing the book summary and generating a prompt for the cover page...")
        # cover_prompt = get_response(book_summary)

        # Step 2: Generate the book cover image based on the generated prompt
        st.write("Generating the book cover image...")
        get_image(book_description)
        # st.markdown("### Generated Prompt:")
        # st.markdown(f"`{cover_prompt}`")

        # Step 3: Display the generated image
        image_path = './gen-img1.png'
        st.image(image_path, caption="Generated Book Cover", use_column_width=True)

        # Step 4: Option to download the image
        with open(image_path, "rb") as img_file:
            btn = st.download_button(
                label="Download Image",
                data=img_file,
                file_name="generated_book_cover.png",
                mime="image/png"
            )
    else:
        st.error("Please enter a book summary to generate a cover!")
