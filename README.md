# SkyBot

A Reddit bot that monitors subreddits for aircraft images and extracts registration numbers using OCR.

## Setup

1. Install dependencies:
```bash
pip3.10 install -r requirements.txt
```

2. Install Tesseract OCR:
```bash
brew install tesseract  # For macOS
```

3. Set up Reddit API credentials:
   - Go to https://www.reddit.com/prefs/apps
   - Click "create another app..."
   - Choose "script"
   - Fill in the required information
   - Once created, you'll get a client ID and client secret

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the `.env` file with your Reddit API credentials:
     - `REDDIT_CLIENT_ID`: Your Reddit client ID
     - `REDDIT_CLIENT_SECRET`: Your Reddit client secret
     - `REDDIT_USER_AGENT`: A descriptive user agent (e.g., "AircraftRegistrationBot/1.0")

## Usage

1. Test OCR on a single image:
```bash
python3.10 ocr_script.py
```

2. Monitor a subreddit for aircraft images:
```bash
python3.10 reddit_monitor.py
```

## Features

- OCR text extraction from images using Tesseract
- Aircraft registration number detection (N-numbers)
- Reddit subreddit monitoring
- Image processing and analysis 