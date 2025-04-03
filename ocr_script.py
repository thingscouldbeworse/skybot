import requests
from PIL import Image
import pytesseract
from io import BytesIO


def extract_text_from_image(image_url):
    # Download the image from the URL
    response = requests.get(image_url)
    if response.status_code != 200:
        print(f"Failed to download image. Status code: {response.status_code}")
        return

    # Convert the image data to a PIL Image object
    image = Image.open(BytesIO(response.content))

    # Try different OCR configurations
    configs = [
        # Default configuration
        "",
        # Use LSTM OCR Engine Mode with legacy character classifier
        "--oem 3 --psm 6",
        # Use LSTM OCR Engine Mode with legacy character classifier and whitelist characters
        "--oem 3 --psm 6 -c tessedit_char_whitelist=N0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        # Use LSTM OCR Engine Mode with legacy character classifier and blacklist characters
        "--oem 3 --psm 6 -c tessedit_char_blacklist=()[]{}",
        # Use LSTM OCR Engine Mode with legacy character classifier and custom dictionary
        "--oem 3 --psm 6 -c tessedit_char_whitelist=N0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ -c tessedit_char_blacklist=()[]{}",
    ]

    all_text = []
    for i, config in enumerate(configs, 1):
        text = pytesseract.image_to_string(image, config=config)
        all_text.append(text.strip())

    # Return the combined text from all configurations
    return "\n".join(all_text)


if __name__ == "__main__":
    # The image URL from Reddit
    image_url = "https://i.redd.it/42dvrq8fippe1.jpeg"
    extract_text_from_image(image_url)
