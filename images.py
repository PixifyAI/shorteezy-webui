import os
import asyncio
from runware import Runware, IImageInference
from dotenv import load_dotenv
import aiohttp
import aiofiles
import logging
from logging.handlers import RotatingFileHandler
import random

# Set up logging
log_file = 'image_generation.log'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load environment variables
load_dotenv()

RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY")

print(RUNWARE_API_KEY)

if not RUNWARE_API_KEY:
    logger.error("RUNWARE_API_KEY is not set in the environment variables")
    raise ValueError("RUNWARE_API_KEY is not set in the environment variables")

async def generate_image(prompt, output_file, size=(1024, 1792), max_retries=3, initial_delay=1):
    runware = Runware(api_key=RUNWARE_API_KEY)
    for attempt in range(max_retries):
        try:
            await runware.connect()
            logger.info(f"Connected to Runware. Generating image for prompt: {prompt} (Attempt {attempt + 1}/{max_retries})")

            request_image = IImageInference(
                positivePrompt=prompt,
                model="runware:100@1",  # Verify this model ID is correct
                numberResults=1,
                negativePrompt="low quality, blurry",
                useCache=False,
                height=size[1],
                width=size[0],
            )

            images = await runware.imageInference(requestImage=request_image)

            if images:
                image_url = images[0].imageURL
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            async with aiofiles.open(output_file, mode='wb') as f:
                                await f.write(await resp.read())
                            logger.info(f"Image saved to {output_file}")
                            return True
                        else:
                            logger.error(f"Failed to download image: HTTP status {resp.status}")
            else:
                logger.warning("No images were generated")
        except Exception as e:
            logger.error(f"An error occurred during image generation (Attempt {attempt + 1}/{max_retries}): {str(e)}")
        
        if attempt < max_retries - 1:
            delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.info(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
    
    logger.error(f"Failed to generate image after {max_retries} attempts.")
    return False

async def create_from_data(data, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    logger.info(f"Creating images in directory: {output_dir}")

    image_number = 0
    for element in data:
        if element["type"] != "image":
            continue
        image_number += 1
        image_name = f"image_{image_number}.webp"
        success = await generate_image(
            element["description"] + ". Vertical image, fully filling the canvas.",
            os.path.join(output_dir, image_name)
        )
        if not success:
            logger.warning(f"Failed to generate image {image_number} after multiple attempts.")

def create_from_data_sync(data, output_dir):
    asyncio.run(create_from_data(data, output_dir))

# If you need to run this file directly for testing
if __name__ == "__main__":
    asyncio.run(generate_image("Test prompt", "test_output.png"))