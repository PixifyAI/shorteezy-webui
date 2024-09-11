import gradio as gr
import os
import json
import time
import requests
from openai import OpenAI
import asyncio
import chardet

# Import functions from existing project files
from narration import parse as parse_narration, create as create_narration
from images import generate_image, create_from_data_sync
from video import create as create_video

# LMStudio API configuration
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

def read_file_with_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
    detected = chardet.detect(raw_data)
    encoding = detected['encoding']
    return raw_data.decode(encoding)

def load_existing_data():
    base_dir = "shorts"
    if not os.path.exists(base_dir) or not os.listdir(base_dir):
        return [], []
    
    try:
        latest_dir = max([os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
        
        data_file = os.path.join(latest_dir, "data.json")
        if not os.path.exists(data_file):
            return [], []
        
        with open(data_file, "r") as f:
            data = json.load(f)
        
        print(f"Loaded data: {data}")  # Debug print
        
        images = []
        narrations = []
        
        if isinstance(data, dict):
            images = data.get("images", [])
            narrations = data.get("narrations", [])
        elif isinstance(data, list):
            images = [item for item in data if isinstance(item, dict) and item.get("type") == "image"]
            narrations = [item.get("content", "") for item in data if isinstance(item, dict) and item.get("type") == "text"]
        else:
            print(f"Unexpected data format in {data_file}")
        
        return images, narrations
    except Exception as e:
        print(f"Error loading existing data: {str(e)}")
        return [], []

def process_input(text_input, url_input):
    if url_input:
        response = requests.get(url_input)
        source_material = response.text
    elif os.path.isfile(text_input):
        source_material = read_file_with_encoding(text_input)
    else:
        source_material = text_input
    
    response = client.chat.completions.create(
        model="lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
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
    
    # Create a new directory for this short
    output_dir = os.path.join("shorts", str(int(time.time())))
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the script to response.txt in the new directory
    with open(os.path.join(output_dir, "response.txt"), "w") as f:
        f.write(response_text)
    
    # Parse the script
    data, narrations = parse_narration(response_text)
    
    # Generate images and narrations
    create_from_data_sync(data, os.path.join(output_dir, "images"))
    create_narration(data, os.path.join(output_dir, "narrations"))
    
    # Save data to JSON file
    with open(os.path.join(output_dir, "data.json"), "w") as f:
        json.dump({"images": data, "narrations": narrations}, f)
    
    return data, narrations

def regenerate_image(image_texts):
    image_prompts = image_texts.split("\n")
    data = [{"type": "image", "description": prompt} for prompt in image_prompts if prompt.strip()]
    output_dir = os.path.join("shorts", str(int(time.time())))
    os.makedirs(output_dir, exist_ok=True)
    create_from_data_sync(data, os.path.join(output_dir, "images"))
    return [os.path.join(output_dir, "images", f"image_{i+1}.webp") for i in range(len(data))]

def regenerate_narration(narration_texts):
    narrations = narration_texts.split("\n")
    data = [{"type": "text", "content": narration} for narration in narrations if narration.strip()]
    output_dir = os.path.join("shorts", str(int(time.time())))
    os.makedirs(output_dir, exist_ok=True)
    create_narration(data, os.path.join(output_dir, "narrations"))
    return [os.path.join(output_dir, "narrations", f"narration_{i+1}.mp3") for i in range(len(data))]

def create_final_video(image_paths, audio_paths):
    num_segments = min(len(image_paths), len(audio_paths))
    video_data = []
    for i in range(num_segments):
        video_data.append({
            "image": image_paths[i],
            "audio": audio_paths[i]
        })
    output_dir = os.path.join("shorts", str(int(time.time())))
    os.makedirs(output_dir, exist_ok=True)
    video_path = create_video(video_data, output_dir)
    return video_path

# Launch the interface
if __name__ == "__main__":
    import sys
    images, narrations = load_existing_data()
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        data, narrations = process_input(input_file, "")
        images = [item for item in data if item["type"] == "image"]
    
    with gr.Blocks() as interface:
        gr.Markdown("# Shorteezy Generator")
        
        with gr.Row():
            text_input = gr.Textbox(label="Enter your text", lines=5)
            url_input = gr.Textbox(label="Or enter a URL")
        
        run_button = gr.Button("RUN")
        
        output_gallery = gr.Gallery(label="Generated Images")
        output_audio = gr.Audio(label="Generated Narrations", type="filepath")
        
        image_texts = gr.Textbox(label="Image Descriptions", lines=5)
        narration_texts = gr.Textbox(label="Narration Texts", lines=5)
        
        regenerate_image_button = gr.Button("Regenerate Image")
        regenerate_narration_button = gr.Button("Regenerate Narration")
        
        create_shorteezy_button = gr.Button("Create Shorteezy")
        video_output = gr.Video(label="Generated Shorteezy")
        
        # Update the interface with the loaded or processed data
        if images:
            output_gallery.value = [os.path.join("shorts", os.path.basename(os.path.dirname(item["description"])), "images", f"image_{i+1}.webp") for i, item in enumerate(images)]
            image_texts.value = "\n".join([item.get("description", "") for item in images])
        if narrations:
            # Change this to use a single audio file instead of a list
            output_audio.value = os.path.join("shorts", os.path.basename(os.path.dirname(narrations[0])), "narrations", "narration_1.mp3")
            narration_texts.value = "\n".join(narrations)
        
        # Define event handlers
        def on_run(text_input, url_input):
            data, narrations = process_input(text_input, url_input)
            images = [item for item in data if item["type"] == "image"]
            return (
                [os.path.join("shorts", os.path.basename(os.path.dirname(item["description"])), "images", f"image_{i+1}.webp") for i, item in enumerate(images)],
                os.path.join("shorts", os.path.basename(os.path.dirname(narrations[0])), "narrations", "narration_1.mp3"),  # Change this to use a single audio file
                "\n".join([item["description"] for item in images]),
                "\n".join(narrations)
            )
        
        run_button.click(
            on_run,
            inputs=[text_input, url_input],
            outputs=[output_gallery, output_audio, image_texts, narration_texts]
        )
        
        regenerate_image_button.click(
            regenerate_image,
            inputs=[image_texts],
            outputs=[output_gallery]
        )
        
        regenerate_narration_button.click(
            regenerate_narration,
            inputs=[narration_texts],
            outputs=[output_audio]
        )
        
        create_shorteezy_button.click(
            create_final_video,
            inputs=[output_gallery, output_audio],
            outputs=[video_output]
        )
    
    interface.launch()