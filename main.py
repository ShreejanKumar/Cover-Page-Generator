import pathlib
import textwrap
import google.generativeai as genai
from IPython.display import display
from IPython.display import Markdown
import vertexai
from vertexai.preview.vision_models import Image, ImageGenerationModel
import os
import google.auth
import json
from google.oauth2 import service_account
from google.auth import credentials
from google.auth.transport.requests import Request
from google.cloud import aiplatform
import streamlit as st

def to_markdown(text):
  text = text.replace('•', ' *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


def get_response(summary):
    gemini_api_key = st.secrets["gemini"]["api_key"]
    genai.configure(api_key=gemini_api_key)
    
    prompt_template = """You’re a knowledgeable book summary analyst with a keen eye for detail and a deep understanding of what makes a compelling book cover. Your experience in design and marketing ensures that you can extract key elements from the text to create impactful visuals and engaging titles.
Your task is to analyze a given book summary and identify the following that would be essential in generating a captivating cover page for the book:
1) The book's genre or significant themes
2) Keywords and concepts
3) The main characters or notable symbols
4) Any setting or important locations
5) The tone or atmosphere
6) Any specific visual elements mentioned (e.g., colors, objects, landscapes)


Once you have completed your analysis, return a detailed prompt that can be directly inputted in a model to generate the cover page of the book.
The prompt doesnt need to include all of the above information but you need to devise a cover page using this information that will fit the best for the book and will be good for marketing the book.
The design should remain appropriate for all audiences, avoiding content that could be perceived as offensive or harmful or violent. Avoid using words like killing, nudity etc. Also avoid using just the portrait of a character as the cover page.
Do not add title for the prompt like "Prompt for Generating Cover Pages for" in the output.
Dont add any text in the image
Here is the Book summary: <<summary>>
"""

    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = prompt_template.replace('<<summary>>', summary)
    response = model.generate_content(prompt)
    return response.text


def get_image(prompt, aspect_ratio):
    gcp_credentials = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(gcp_credentials)
    gcp_project_id = gcp_credentials["project_id"]
    aiplatform.init(project=gcp_project_id, credentials=credentials)

    prompt_template = """ Generate an art with the description given below. Ensure no text is present in the image.
Ignore the book name and the authors name.
Avoid any specific characters or copyrighted figures, ensuring compliance with community guidelines.
Ensure that you generate just the art and not the actual image of a book. 
<<desc>>
"""

    neg_prompt = "Dont write any text"
    image_prompt = prompt_template.replace('<<desc>>', prompt)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
    image = model.generate_images(prompt=image_prompt, negative_prompt = neg_prompt, aspect_ratio = aspect_ratio )
    image[0].save(location="./gen-img1.png", include_generation_parameters=True)