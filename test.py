import time
import json
import logging
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from browser_utils import launch_debug_chrome, attach_to_chrome

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("automation.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

filled_fields = set()

def load_links():
    try:
        with open(config["output_file"], "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"❌ Output file not found: {config['output_file']}")
        return []

def click_apply_now_button(driver):
    try:
        apply_span = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.css-1ebo7dz.eu4oa1w0"))
        )
        button = apply_span.find_element(By.XPATH, "./ancestor::button")
        driver.execute_script("arguments[0].click();", button)
        logging.info("🟢 Clicked 'Apply now' button.")
        return True
    except Exception as e:
        logging.warning(f"⚠️ 'Apply now' button not found or clickable: {e}")
        return False

def fill_form_with_validation(driver):
    all_required_filled = True

    for key, field in config.get("application_details", {}).items():
        field_type = field.get("type")
        value = field.get("value")
        click = field.get("click", False)

        if field_type in ["text", "textarea"]:
            xpath = field.get("xpath")
            if xpath:
                try:
                    input_elem = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    label_xpath = xpath + "/preceding::label[1]"
                    label_elem = driver.find_element(By.XPATH, label_xpath)
                    is_required = "*" in label_elem.text

                    if value:
                        input_elem.clear()
                        input_elem.send_keys(str(value))
                        logging.info(f"[fill_form] Filled '{key}' with: {value}")
                    elif is_required:
                        all_required_filled = False
                        logging.warning(f"[fill_form] Required field '{key}' missing in config.")
                except Exception as e:
                    if is_required:
                        logging.warning(f"[fill_form] Required text field '{key}' failed: {e}")
                        all_required_filled = False

        elif field_type == "radio_group":
            xpath_group = field.get("xpath_group")
            if xpath_group:
                try:
                    options = driver.find_elements(By.XPATH, xpath_group)
                    matched = False
                    for option in options:
                        label = option.text.strip()
                        if value and value.lower() in label.lower():
                            driver.execute_script("arguments[0].scrollIntoView(true);", option)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", option)
                            logging.info(f"[fill_form] Selected radio '{value}' for '{key}'")
                            matched = True
                            break

                    if not matched:
                        label_elem = driver.find_element(By.XPATH, xpath_group + "/preceding::label[1]")
                        is_required = "*" in label_elem.text
                        if is_required:
                            all_required_filled = False
                            logging.warning(f"[fill_form] Required radio group '{key}' mismatch.")
                except Exception as e:
                    logging.warning(f"[fill_form] Radio group '{key}' error: {e}")
                    try:
                        label_elem = driver.find_element(By.XPATH, xpath_group + "/preceding::label[1]")
                        if "*" in label_elem.text:
                            all_required_filled = False
                    except:
                        pass

        elif field_type == "checkbox":
            xpath = field.get("xpath")
            if xpath and click:
                try:
                    checkbox = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", checkbox)
                    logging.info(f"[fill_form] Checked '{key}'")
                except Exception as e:
                    logging.warning(f"[fill_form] Optional checkbox '{key}' could not be clicked: {e}")

    return all_required_filled

def wait_and_click(driver, selectors, timeout=10):
    for selector in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            driver.execute_script("arguments[0].click();", elem)
            logging.info(f"➡️ Clicked: {selector}")
            return True
        except:
            continue
    return False

def process_application_steps(driver):
    max_steps = 15
    steps = 0

    while steps < max_steps:
        steps += 1
        logging.info(f"🌀 Step {steps}...")

        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form, input, textarea, select"))
            )
            logging.info("📝 Form fields detected.")
            all_required_filled = fill_form_with_validation(driver)
            if not all_required_filled:
                input("⏸️ Fill missing fields manually then press Enter to continue...")
        except TimeoutException:
            logging.info("ℹ️ No form fields on this step.")

        try:
            submit_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ia-SubmitButton"))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", submit_button)
            submit_button.click()
            logging.info("✅ Submitted application successfully.")
            return True
        except:
            pass

        clicked = wait_and_click(driver, [
            "button.ia-ContinueButton",
            "button.ia-ApplyAnywayButton",
            "button[type='submit']",
            "button[data-testid='form-submit-button']",
            "button[data-tn-element='continueButton']",
            "button[aria-label='Continue']"
        ], timeout=5)

        if clicked:
            logging.info("➡️ Clicked 'Continue'.")
            time.sleep(2)
            continue

        logging.warning("⚠️ No Continue/Submit found. Waiting for manual input...")
        input("👀 Please handle manually and press Enter to proceed...")

    logging.error("❌ Max steps reached. Ending process.")
    return False

def apply_to_job(driver, job_url):
    try:
        driver.get(job_url)
        logging.info(f"🌐 Opened job: {job_url}")
        time.sleep(3)

        if not click_apply_now_button(driver):
            logging.info("⏭️ No 'Apply now' button, skipping.")
            return False

        success = process_application_steps(driver)
        if success:
            logging.info("🏁 Finished application.")
        return success

    except Exception as e:
        logging.error(f"❌ Error applying to job: {job_url} — {e}")
        return False

def main():
    driver = None
    try:
        launch_debug_chrome()
        driver = attach_to_chrome()
    except Exception as e:
        logging.critical(f"🚫 Chrome error: {e}")
        return

    links = load_links()
    logging.info(f"📄 Total jobs: {len(links)}")

    for i, link in enumerate(links, 1):
        logging.info(f"\n📌 Applying {i}/{len(links)}")
        filled_fields.clear()
        success = apply_to_job(driver, link)

        if not success:
            logging.warning("⚠️ Skipped due to failure.")

    logging.info("🎉 Done with all jobs.")

    if driver:
        driver.quit()
        logging.info("🛑 Browser closed.")

if __name__ == "__main__":
    main()
