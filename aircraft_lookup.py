import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def setup_selenium_driver():
    """Setup and return a configured Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    return webdriver.Chrome(options=chrome_options)


def print_progress(message, success=None):
    """Print a progress message with an indicator."""
    if success is None:
        indicator = "⏳"  # Waiting
    elif success:
        indicator = "✅"  # Success
    else:
        indicator = "❌"  # Failed
    print(f"{indicator} {message}")


def get_latest_flight_status_selenium(url):
    """Fetch and parse the latest flight status from Flightradar24 using Selenium."""
    try:
        print("\n🔄 Starting Selenium process...")
        print_progress("Initializing Chrome WebDriver")
        driver = setup_selenium_driver()
        print_progress("WebDriver initialized", True)

        try:
            print_progress("Loading page URL")
            driver.get(url)
            print_progress("Page load started", True)

            # Wait for the table to load
            wait = WebDriverWait(driver, 20)

            try:
                print_progress("Waiting for data table to appear")
                table = wait.until(
                    EC.presence_of_element_located((By.ID, "tbl-datatable"))
                )
                print_progress("Data table found", True)

                print_progress("Waiting for loading message to disappear")
                wait.until(
                    EC.invisibility_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'Loading')]")
                    )
                )
                print_progress("Loading message disappeared", True)

                print_progress("Waiting for JavaScript data population")
                time.sleep(5)
                print_progress("Extra wait time completed", True)

                print("\n🔍 Searching for flight data...")

                # Find all rows in the table
                rows = table.find_elements(By.TAG_NAME, "tr")

                # Skip header row
                data_rows = rows[1:]

                recent_flight = None
                next_flight = None

                # Look through rows to find most recent landed flight and next estimated flight
                for row in data_rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 12:  # Skip rows without enough cells
                        continue

                    status_cell = cells[11]
                    status_text = status_cell.text.strip()

                    # Extract flight info from the row
                    flight_info = {
                        "date": cells[2].text.strip(),
                        "from": cells[3].text.strip(),
                        "to": cells[4].text.strip(),
                        "flight_number": cells[5].text.strip(),
                        "status": status_text,
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Check if this is a landed flight
                    if "Landed" in status_text and not recent_flight:
                        recent_flight = flight_info
                        print("\n✈️ Found most recent flight:")
                        print(f"  • Date: {flight_info['date']}")
                        print(f"  • Flight: {flight_info['flight_number']}")
                        print(f"  • From: {flight_info['from']}")
                        print(f"  • To: {flight_info['to']}")
                        print(f"  • Status: {flight_info['status']}")

                    # Check if this is an estimated departure
                    if "Estimated" in status_text and not next_flight:
                        next_flight = flight_info
                        print("\n✈️ Found next flight:")
                        print(f"  • Date: {flight_info['date']}")
                        print(f"  • Flight: {flight_info['flight_number']}")
                        print(f"  • From: {flight_info['from']}")
                        print(f"  • To: {flight_info['to']}")
                        print(f"  • Status: {flight_info['status']}")

                    # If we found both flights, we can stop looking
                    if recent_flight and next_flight:
                        break

                result = {
                    "recent_flight": recent_flight if recent_flight else None,
                    "next_flight": next_flight if next_flight else None,
                    "timestamp": datetime.now().isoformat(),
                }

                return result

            except Exception as e:
                print_progress(
                    f"Error while waiting for or parsing data: {str(e)}", False
                )
                print("\n🔍 Debug Information:")
                print("  • Current URL:", driver.current_url)
                print("  • Page Title:", driver.title)
                print("  • Error Type:", type(e).__name__)
                return None

        finally:
            print_progress("Closing WebDriver")
            driver.quit()
            print_progress("WebDriver closed", True)

    except Exception as e:
        print_progress(f"Selenium error: {str(e)}", False)
        print("\n❌ Error Details:")
        print(f"  • Type: {type(e).__name__}")
        import traceback

        print("  • Traceback:")
        for line in traceback.format_exc().split("\n"):
            print(f"    {line}")
        return None


def generate_fr24_url(registration):
    """Generate a Flightradar24 URL for an aircraft registration."""
    base_url = "https://www.flightradar24.com/data/aircraft/"
    # Remove the hyphen from registration for URL
    clean_reg = registration.replace("-", "").lower()
    return f"{base_url}{clean_reg}"


def process_registration(registration):
    """Process an aircraft registration and return relevant information."""
    if not registration:
        return None

    fr24_url = generate_fr24_url(registration)
    result = {"registration": registration, "fr24_url": fr24_url}

    # Try to get the flight status using Selenium
    flight_data = get_latest_flight_status_selenium(fr24_url)
    if flight_data:
        result.update(flight_data)

    return result


if __name__ == "__main__":
    # Example usage
    test_reg = "OY-RCM"
    result = process_registration(test_reg)
    if result:
        print(f"Aircraft Registration: {result['registration']}")
        print(f"Flightradar24 URL: {result['fr24_url']}")

        if result.get("recent_flight"):
            flight = result["recent_flight"]
            print("\nMost Recent Flight:")
            print(f"  Date: {flight['date']}")
            print(f"  Flight Number: {flight['flight_number']}")
            print(f"  From: {flight['from']}")
            print(f"  To: {flight['to']}")
            print(f"  Status: {flight['status']}")

        if result.get("next_flight"):
            flight = result["next_flight"]
            print("\nNext Scheduled Flight:")
            print(f"  Date: {flight['date']}")
            print(f"  Flight Number: {flight['flight_number']}")
            print(f"  From: {flight['from']}")
            print(f"  To: {flight['to']}")
            print(f"  Status: {flight['status']}")
