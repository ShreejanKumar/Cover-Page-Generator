import pathlib
import textwrap
from io import BytesIO
import IPython
import time
import PIL.Image
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
import requests
import httpx

def to_markdown(text):
  text = text.replace('•', ' *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


def send_generation_request(host, params,):
    STABILITY_KEY = st.secrets["stability"]["api_key"]
    headers = {
        "Accept": "image/*",
        "Authorization": f"Bearer {STABILITY_KEY}"
    }

    # Encode parameters
    files = {}
    image = params.pop("image", None)
    mask = params.pop("mask", None)
    if image is not None and image != '':
        files["image"] = open(image, 'rb')
    if mask is not None and mask != '':
        files["mask"] = open(mask, 'rb')
    if len(files)==0:
        files["none"] = ''

    # Send request
    response = requests.post(
        host,
        headers=headers,
        files=files,
        data=params
    )
    if not response.ok:
        st.error(f"An error occurred: {response.status_code}: {response.text}")

    return response

def get_response(prompt, aspect_ratio):
    STABILITY_KEY = st.secrets["stability"]["api_key"]
    
    # Generating First Image
    negative_prompt = "Don't write any text"
    seed = 0 
    output_format = "png"
    
    host = f"https://api.stability.ai/v2beta/stable-image/generate/sd3"
    
    params = {
        "prompt" : prompt,
        "negative_prompt" : negative_prompt,
        "aspect_ratio" : aspect_ratio,
        "seed" : seed,
        "output_format" : output_format,
        "model" : "sd3.5-large",
        "mode" : "text-to-image"
    }
    
    response = send_generation_request(
        host,
        params
    )
    
    # Decode response
    output_image = response.content
    finish_reason = response.headers.get("finish-reason")
    seed = response.headers.get("seed")
    
    # Check for NSFW classification
    if finish_reason == 'CONTENT_FILTERED':
        raise Warning("Generation failed NSFW classifier")

    path = f"./generated_{seed}.{output_format}"
    with open(path, "wb") as f:
        f.write(output_image)
    # st.image(path, caption="Generated Image", use_column_width=True)

    # Checking Image with LLM
    gemini_api_key = st.secrets["gemini"]["api_key"]
    genai.configure(api_key=gemini_api_key)
    gcp_credentials = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(gcp_credentials)
    gcp_project_id = gcp_credentials["project_id"]
    aiplatform.init(project=gcp_project_id, credentials=credentials)
    prompt_template = """I am giving you an Image and a prompt. I want you to analyse that Image and check if all the things mentioned in the prompt are present in it. IF they are present then return just True (Dont write anything else). Otherwise return a prompt in a similar way as the old prompt that contains only the changes that needs to made in the image. Bear in mind the details of the original prompt and dont give any instructions against that. Here is the prompt <<prompt>>"""

    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt_llm = prompt_template.replace('<<prompt>>', prompt)
    sample_file_1 = PIL.Image.open(path)
    response = model.generate_content([prompt, sample_file_1])
    st.write(response.text)
    # Regenerating Image with missing details
    if response.text != 'True':
        strength = 0.40
        params = {
            "image" : path,
            "prompt" : response.text,
            "negative_prompt" : negative_prompt,
            "strength" : strength,
            "seed" : seed,
            "output_format": output_format,
            "model" : "sd3.5-large",
            "mode" : "image-to-image"
        }
        
        response = send_generation_request(
            host,
            params
        )
        
        # Decode response
        output_image = response.content
        finish_reason = response.headers.get("finish-reason")
        seed = response.headers.get("seed")
        
        # Check for NSFW classification
        if finish_reason == 'CONTENT_FILTERED':
            raise Warning("Generation failed NSFW classifier")
        
        # Save and display result
        generated = f"generated_{seed}.{output_format}"
        with open(generated, "wb") as f:
            f.write(output_image)
        image_paths = [generated]
        return image_paths
    image_paths = [path]
    return image_paths


def get_image(prompt, aspect_ratio, number_of_images=4):
    gcp_credentials = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(gcp_credentials)
    gcp_project_id = gcp_credentials["project_id"]
    aiplatform.init(project=gcp_project_id, credentials=credentials)

    prompt_template = """Generate an art with the description given below. Ensure no text is present in the image.
Ignore the book name and the author's name.
Avoid any specific characters or copyrighted figures, ensuring compliance with community guidelines.
Ensure that you generate just the art and not the actual image of a book. 
<<desc>>
"""
    neg_prompt = "Don't write any text"
    image_prompt = prompt_template.replace('<<desc>>', prompt)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
    images = model.generate_images(prompt=image_prompt, negative_prompt=neg_prompt, aspect_ratio=aspect_ratio, number_of_images=number_of_images)

    image_paths = []
    for idx, img in enumerate(images):
        path = f"./gen-img{idx+1}.png"
        img.save(location=path, include_generation_parameters=True)
        image_paths.append(path)
    return image_paths