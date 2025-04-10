import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from browser_utils import launch_debug_chrome, attach_to_chrome

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_application.log'),
        logging.StreamHandler()
    ]
)

# Load job links from file
def load_job_links(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        logging.info(f"Loaded {len(links)} job links from {file_path}")
        return links
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        return []

# Switch to iframe if necessary
def switch_to_iframe(driver):
    try:
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            driver.switch_to.frame(iframe)
            logging.info("Switched to iframe.")
            return True
    except Exception as e:
        logging.error(f"Error while switching to iframe: {e}")
    return False

# Function to find and click one of multiple possible selectors using JavaScript
def find_and_click_button(driver, locators, max_scrolls=5):
    """Tries multiple locator strategies (ID, Name, etc.) to find and click the correct button."""
    for locator in locators:
        for attempt in range(max_scrolls):
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(locator)
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", element)  # Ensure element is in view
                driver.execute_script("arguments[0].click();", element)  # Perform JavaScript click
                logging.info(f"Clicked button with locator: {locator}")
                return True
            except NoSuchElementException:
                logging.info(f"Scrolling to search for element: {locator} (Attempt {attempt + 1}/{max_scrolls})")
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1)
            except TimeoutException:
                logging.warning(f"Element not found within timeout: {locator}")
            except WebDriverException as e:
                logging.error(f"Error clicking button with locator {locator}: {e}")
    return False

# Function to apply for a job
def apply_for_job(driver, job_url, button_selectors):
    try:
        driver.get(job_url)
        logging.info(f"Navigated to job URL: {job_url}")
        time.sleep(3)

        # Handle iframe if present
        within_iframe = switch_to_iframe(driver)

        # Click "Apply Now"
        try:
            apply_now_clicked = find_and_click_button(driver, button_selectors['apply_now'])
            if not apply_now_clicked:
                logging.warning("Apply Now button not found. Skipping this job.")
                return
        except Exception as e:
            logging.error(f"Error clicking 'Apply Now' button: {e}")
            return

        # Continue clicking buttons until submission
        while True:
            # Try to find and click one of the "Continue" buttons
            continue_clicked = find_and_click_button(driver, button_selectors['continue'])
            if continue_clicked:
                time.sleep(2)
                continue
            else:
                logging.info("No 'Continue' button found on this page.")

            # Try to find "Apply anyway" button
            apply_anyway_clicked = find_and_click_button(driver, button_selectors['apply_anyway'])
            if apply_anyway_clicked:
                time.sleep(2)

                # Look for "Continue applying" button
                continue_applying_clicked = find_and_click_button(driver, button_selectors['continue_applying'])
                if continue_applying_clicked:
                    time.sleep(2)

            # Check for "Submit Your Application" button
            submit_clicked = find_and_click_button(driver, button_selectors['submit'])
            if submit_clicked:
                logging.info("Clicked 'Submit Your Application' button")
                return  # Exit loop after submission
            else:
                logging.warning("Submit Your Application button not found. Manual intervention may be required.")
                return

    except Exception as e:
        logging.error(f"Error while applying for job at {job_url}: {e}")
    finally:
        if within_iframe:
            driver.switch_to.default_content()  # Switch back to main content after processing the iframe

# Main function
def main():
    # Define button selectors using ID, Name, or fallback to other attributes
    button_selectors = {
        'apply_now': [
            (By.ID, 'indeedApplyButton'),  # Try locating button by ID
            (By.NAME, 'apply'),           # Try locating button by Name (if available)
        ],
        'continue': [
            (By.ID, 'continue-button'),   # Try locating by ID for first variant
            (By.NAME, 'continue'),        # Try locating by Name for second variant
            (By.XPATH, "//button[@data-testid='continue-button']"),  # Fallback to XPath
            (By.XPATH, "//button[contains(@class, 'f471b073d')]")    # Fallback to class-based XPath
        ],
        'apply_anyway': [
            (By.ID, 'apply-anyway-button'),  # Hypothetical ID (replace with actual ID if available)
            (By.NAME, 'apply_anyway'),       # Hypothetical Name (replace with actual Name if available)
            (By.XPATH, "//span[text()='Apply anyway']")  # Fallback to XPath
        ],
        'continue_applying': [
            (By.ID, 'continue-applying'),    # Hypothetical ID (replace with actual ID if available)
            (By.NAME, 'continue_applying'),  # Hypothetical Name (replace with actual Name if available)
            (By.XPATH, "//span[text()='Continue applying']")  # Fallback to XPath
        ],
        'submit': [
            (By.ID, 'submit-application'),  # Hypothetical ID (replace with actual ID if available)
            (By.NAME, 'submit'),            # Try locating by Name
            (By.XPATH, "//button[contains(@class, 'f471b073d') and contains(@class, 'css-14m9ps3')]")  # Fallback to XPath
        ]
    }

    # Launch browser
    launch_debug_chrome()
    driver = attach_to_chrome()

    # Load job links from file
    job_links = load_job_links('easily_apply_jobs.txt')

    # Start applying for jobs
    for job_url in job_links:
        apply_for_job(driver, job_url, button_selectors)

    # Close browser
    driver.quit()
    logging.info("Finished applying for all jobs.")

if __name__ == "__main__":
    main()