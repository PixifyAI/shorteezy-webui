from TTS.api import TTS
import os
import time
import random
import logging
from logging.handlers import RotatingFileHandler

# Set up logging
log_file = 'narration_generation.log'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def parse(narration):
    data = []
    narrations = []
    lines = narration.split("\n")
    for line in lines:
        if line.startswith('Narrator: '):
            text = line.replace('Narrator: ', '')
            data.append({
                "type": "text",
                "content": text.strip('"'),
            })
            narrations.append(text.strip('"'))
        elif line.startswith('['):
            background = line.strip('[]')
            data.append({
                "type": "image",
                "description": background,
            })
    return data, narrations

def generate_speech(tts, text, output_file, max_retries=3, initial_delay=1):
    for attempt in range(max_retries):
        try:
            tts.tts_to_file(text=text, file_path=output_file)
            logger.info(f"Generated narration: {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error generating narration (Attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
    
    logger.error(f"Failed to generate narration after {max_retries} attempts.")
    return False

def create(data, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Initialize TTS
    tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")

    n = 0
    for element in data:
        if element["type"] != "text":
            continue

        n += 1
        output_file = os.path.join(output_folder, f"narration_{n}.mp3")

        # Generate speech with retry logic
        success = generate_speech(tts, element["content"], output_file)
        if not success:
            logger.warning(f"Failed to generate narration {n} after multiple attempts.")

    logger.info(f"Generated {n} narration files in {output_folder}")