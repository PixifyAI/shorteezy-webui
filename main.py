#!/usr/bin/env python3

from openai import OpenAI
import time
import json
import sys
import os
import requests
from urllib.parse import urlparse
import chardet

import narration
import images
import video

# LMStudio API configuration
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

def detect_encoding(content):
    result = chardet.detect(content)
    return result['encoding']

def read_file_with_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_content = file.read()
    encoding = detect_encoding(raw_content)
    return raw_content.decode(encoding)

def fetch_url_content(url):
    response = requests.get(url)
    response.raise_for_status()
    encoding = detect_encoding(response.content)
    return response.content.decode(encoding)

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <source_file_or_url> [settings_file]")
    sys.exit(1)

source_input = sys.argv[1]
is_url = bool(urlparse(source_input).scheme)

try:
    if is_url:
        source_material = fetch_url_content(source_input)
    else:
        source_material = read_file_with_encoding(source_input)
except Exception as e:
    print(f"Error reading input: {e}")
    sys.exit(1)

caption_settings = {}
if len(sys.argv) > 2:
    try:
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            caption_settings = json.load(f)
    except Exception as e:
        print(f"Error reading settings file: {e}")
        sys.exit(1)

short_id = str(int(time.time()))
output_file = "Shorteezy.avi"

basedir = os.path.join("shorts", short_id)
if not os.path.exists(basedir):
    os.makedirs(basedir)

print("Generating Shorteezy script...")

# LMStudio API call
response = client.chat.completions.create(
    model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",  # Replace with the appropriate model identifier
    messages=[
        {
            "role": "system",
            "content": """You are a YouTube Shorts content creator, specifically a narration and image prompt generator.

Your task: Generate a 45-second to 1-minute YouTube Shorts script, including both the narration and image prompts for an AI image generator.

Instructions:

Provide a sequence of image descriptions in square brackets. Each description should represent a visual cue for a single sentence or short phrase in your narration.
Below each image description, provide the corresponding narration.
The narration should be suitable for a text-to-speech engine, meaning no special characters or complex formatting.
Feel free to use any content, including real names and references, as long as it is appropriate and adheres to YouTube's community guidelines.
The images should transition smoothly, creating a dynamic visual backdrop for the narration.
Example Output Format:

###

[Description of a background image]

Narrator: "One sentence of narration"

[Description of a background image]

Narrator: "One sentence of narration"

[Description of a background image]

Narrator: "One sentence of narration"

###

Example Output:

###

[A vibrant sunset over a bustling city skyline.]
"The city never sleeps, and neither does our team."

[A close-up shot of a smiling scientist looking at a microscope.]
"Dr. Emily Carter has been working tirelessly on a breakthrough."

###

By following this format, you'll provide a complete script for a YouTube Shorts video, ready to be used with an AI image generator and a text-to-speech engine.

The short should be 10 sentences maximum.

Add a description of a fitting background image in between all of the narrations. It will later be used to generate an image with AI.
"""
        },
        {
            "role": "user",
            "content": f"Create a YouTube short narration based on the following source material:\n\n{source_material}"
        }
    ],
    temperature=0.7,
)

response_text = response.choices[0].message.content
response_text = response_text.replace("'", "'").replace("`", "'").replace("…", "...").replace(""", '"').replace(""", '"')

response_file_path = os.path.join(basedir, "response.txt")
with open(response_file_path, "w", encoding='utf-8') as f:
    f.write(response_text)

print(f"\nScript generated and saved to {response_file_path}")
print("Please review and edit the script if needed.")
input("Press Enter to continue Shorteezy when you're done editing...")

# Re-read the potentially edited response
with open(response_file_path, "r", encoding='utf-8') as f:
    response_text = f.read()

data, narrations = narration.parse(response_text)
with open(os.path.join(basedir, "data.json"), "w", encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)

print(f"Generating narration...")
narration.create(data, os.path.join(basedir, "narrations"))

print("Generating images...")
images.create_from_data_sync(data, os.path.join(basedir, "images"))

print("Generating video...")
video.create(narrations, basedir, output_file)

print(f"Finished! Here's your Shorteezy video: {os.path.join(basedir, output_file)}")