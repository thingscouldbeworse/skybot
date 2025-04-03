import praw
import re
from ocr_script import extract_text_from_image
from aircraft_lookup import process_registration
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def is_aircraft_registration(text):
    """Check if text contains an aircraft registration number."""
    # Pattern for aircraft registrations (e.g., OY-RCM, G-ABCD, N12345)
    pattern = r"[A-Z]{1,2}-[A-Z0-9]{2,5}"
    return bool(re.search(pattern, text))


def is_image_url(url):
    """Check if a URL points to an image."""
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",  # Common formats
        ".webp",  # Web-optimized format
        ".bmp",
        ".tiff",
        ".tif",  # Other standard formats
        ".heic",
        ".heif",  # High-efficiency formats
    ]
    return any(url.lower().endswith(ext) for ext in image_extensions)


def load_processed_submissions():
    """Load the list of previously processed submission IDs from CSV."""
    try:
        with open("submissions.csv", "r") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()


def save_processed_submission(submission_id):
    """Append a processed submission ID to the CSV file."""
    with open("submissions.csv", "a") as f:
        f.write(f"{submission_id}\n")


def get_image_urls_from_submission(submission):
    """Extract image URLs from a submission, handling both direct images and galleries."""
    if hasattr(submission, "gallery_data"):
        # Handle gallery posts
        image_urls = []
        try:
            # Get the media metadata which contains the actual image URLs
            media_metadata = submission.media_metadata
            for item_id in submission.gallery_data["items"]:
                media_id = item_id["media_id"]
                if media_id in media_metadata:
                    # Get the largest available image
                    image_data = media_metadata[media_id]
                    if "s" in image_data:
                        image_urls.append(image_data["s"]["u"])
            return image_urls
        except Exception as e:
            print(f"\n⚠️  Error processing gallery: {str(e)}")
            return []
    elif not submission.is_self and is_image_url(submission.url):
        # Handle direct image posts
        return [submission.url]
    return []


def process_subreddit(subreddit_name):
    # Initialize Reddit instance with write permissions
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
    )

    # Get the subreddit
    subreddit = reddit.subreddit(subreddit_name)

    # Load previously processed submissions
    processed_submissions = load_processed_submissions()
    print(f"Loaded {len(processed_submissions)} previously processed submissions")

    print(f"\nMonitoring r/{subreddit_name} for new submissions...")
    print("-" * 50)

    # Process hot submissions
    for submission in subreddit.hot(limit=25):
        # Skip if already processed
        if submission.id in processed_submissions:
            print(f"\n⏭️  Skipping submission: {submission.title}")
            print(f"   ID: {submission.id}")
            continue

        # Get all image URLs from the submission
        image_urls = get_image_urls_from_submission(submission)

        if not image_urls:
            print(f"\n⏩  Skipping non-image submission: {submission.title}")
            print(f"   URL: {submission.url}")
            continue

        print(
            f"\n📸 Processing submission with {len(image_urls)} image(s): {submission.title}"
        )

        # Process each image in the submission
        all_registrations = {}
        for i, image_url in enumerate(image_urls, 1):
            print(f"\nProcessing image {i}/{len(image_urls)}")
            print(f"URL: {image_url}")

            # Extract text from image
            text = extract_text_from_image(image_url)

            # Extract registration number from text
            registration = extract_registrations(text)

            if registration:
                print(f"Found aircraft registration: {registration}")
                result = process_registration(registration)

                if result:
                    all_registrations[registration] = result

        # Post a single comment with all registrations found
        if all_registrations:
            post_comment(submission, all_registrations)
        else:
            print("No valid aircraft registrations found in any images.")

        # Record that we've processed this submission
        save_processed_submission(submission.id)
        processed_submissions.add(submission.id)
        print("-" * 50)


def format_flight_info(result):
    """Format flight information into a Reddit-friendly markdown comment."""
    comment = []
    comment.append(f"Aircraft Registration: **{result['registration']}**")
    comment.append(f"[View on Flightradar24]({result['fr24_url']})")

    if result.get("recent_flight"):
        flight = result["recent_flight"]
        comment.append("\n**Most Recent Flight:**")
        comment.append(f"* Flight: {flight['flight_number']}")
        comment.append(f"* Route: {flight['from']} → {flight['to']}")
        comment.append(f"* Date: {flight['date']}")
        comment.append(f"* Status: {flight['status']}")

    if result.get("next_flight"):
        flight = result["next_flight"]
        comment.append("\n**Next Scheduled Flight:**")
        comment.append(f"* Flight: {flight['flight_number']}")
        comment.append(f"* Route: {flight['from']} → {flight['to']}")
        comment.append(f"* Date: {flight['date']}")
        comment.append(f"* Status: {flight['status']}")

    comment.append(
        "\n^(I am a bot that finds aircraft registrations in images and looks up their flight information)"
    )

    return "\n".join(comment)


def post_comment(submission, registrations_info):
    """Post a comment with flight information on the submission."""
    if not registrations_info:
        return

    # Format all registration information into one comment
    comment_parts = []
    for reg, info in registrations_info.items():
        comment_parts.append(format_flight_info(info))
        comment_parts.append("\n---\n")  # Separator between multiple registrations

    # Remove the last separator
    if comment_parts:
        comment_parts.pop()

    # Join all parts and post the comment
    comment_text = "\n".join(comment_parts)
    try:
        comment = submission.reply(comment_text)
        print(f"\n✅ Posted comment: {comment.permalink}")
    except Exception as e:
        print(f"\n❌ Error posting comment: {str(e)}")


def extract_registrations(text):
    """Extract aircraft registrations from text."""
    # First, clean up any extra whitespace and make text consistent
    text = re.sub(r"\s+", " ", text).strip()
    print("\nProcessed text:", text)  # Debug output

    registrations = []

    # Common registration patterns
    patterns = [
        # N-numbers (US) - Must be N followed by at least 2 digits/letters
        (r"N[1-9][0-9A-Z]{1,4}(?![A-Z0-9-])", "N-number"),
        # Standard hyphenated (e.g., G-ABCD, OY-RCM)
        (
            r"(?:G|OY|SE|PH|D|F|EC|HB|TC|VH|ZK|JA|HL|B|VT|EI|4X|P4|A6|VP|C|LV|LN|SP|CS|RA|HS|RP|9M|PK)-[A-Z0-9]{3,5}(?![A-Z0-9-])",
            "Hyphenated",
        ),
    ]

    # Words that often create false positives
    false_positives = {
        "3D-ANSICHT",
        "3D-VIEW",
        "D-ANSIC",
        "F-SUR",
        "D-INFO",
        "3D-AI",
        "D-VIEW",
        "F-SHARE",
        "D-MENU",
        "N-MENU",
    }

    for pattern, reg_type in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            registration = match.group(0).upper()

            # Skip if it's a known false positive
            if registration in false_positives:
                print(f"Skipping false positive: {registration}")
                continue

            # Clean up common OCR errors
            registration = registration.replace(
                "O", "0"
            )  # Replace O with 0 in registrations

            # Skip duplicates
            if registration not in registrations:
                print(f"Found {reg_type}: {registration}")
                registrations.append(registration)

    # If we found any registrations, return the first one
    # In the future, we might want to return all of them or pick based on some criteria
    if registrations:
        return registrations[0]

    return None


def process_submission(submission):
    """Process a submission and extract aircraft registration numbers."""
    print(f"\nProcessing submission: {submission.title}")
    print(f"URL: {submission.url}")

    # Extract text from image if it's an image post
    if is_image_url(submission.url):
        text = extract_text_from_image(submission.url)
    else:
        text = submission.selftext

    # Extract registration number from text
    registration = extract_registrations(text)

    if registration:
        print(f"Found aircraft registration: {registration}")
        result = process_registration(registration)

        if result:
            print(f"- {registration}")
            print(f"  Flightradar24: {result['fr24_url']}")

            if result.get("recent_flight"):
                flight = result["recent_flight"]
                print("  Most Recent Flight:")
                print(f"    Flight: {flight['flight_number']}")
                print(f"    Route: {flight['from']} → {flight['to']}")
                print(f"    Date: {flight['date']}")
                print(f"    Status: {flight['status']}")

            if result.get("next_flight"):
                flight = result["next_flight"]
                print("  Next Scheduled Flight:")
                print(f"    Flight: {flight['flight_number']}")
                print(f"    Route: {flight['from']} → {flight['to']}")
                print(f"    Date: {flight['date']}")
                print(f"    Status: {flight['status']}")

            # Post comment with the registration info
            post_comment(submission, {registration: result})
    else:
        print("No valid aircraft registration found in this image.")

    print("-" * 50)


if __name__ == "__main__":
    subreddit_name = "SkyTagBotStaging"
    process_subreddit(subreddit_name)
