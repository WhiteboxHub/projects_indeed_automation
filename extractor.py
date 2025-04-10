import time
import json
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from browser_utils import launch_debug_chrome, attach_to_chrome

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

def search_jobs(driver):
    try:
        driver.get("https://www.indeed.com")
        logging.info("Navigated to Indeed home page")
        time.sleep(3)

        # Click 'Home' if necessary
        try:
            home_link = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#FindJobs"))
            )
            home_link.click()
            logging.info("Clicked on Home link")
        except:
            logging.info("Home link not found or already on home")

        time.sleep(2)

        # Enter job title
        what_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#text-input-what"))
        )
        what_input.clear()
        what_input.send_keys(config['job_title'])
        logging.info(f"Entered job title: {config['job_title']}")
        time.sleep(1)

        # Click 'Find Jobs'
        find_jobs_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.yosegi-InlineWhatWhere-primaryButton"))
        )
        find_jobs_button.click()
        logging.info("Clicked 'Find jobs' button")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
        )
        logging.info("Job search results loaded")

        # --- Apply Date Posted Filter ---
        try:
            time.sleep(2)
            date_filter_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button#fromAge_filter_button"))
            )
            date_filter_btn.click()
            logging.info("Clicked on Date Posted filter")

            time.sleep(2)
            date_links = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[data-reach-menu-item][role='menuitem']"))
            )
            for option in date_links:
                if config['date_posted'].lower() in option.text.strip().lower():
                    option.click()
                    logging.info(f"Selected Date Posted filter: {option.text.strip()}")
                    break
        except Exception as e:
            logging.warning(f"Failed to apply Date Posted filter: {e}")

        # --- Apply Location Filter ---
        try:
            time.sleep(2)
            location_filter_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "filter-Location"))
            )
            location_filter_btn.click()
            logging.info("Clicked Location filter")
            time.sleep(2)

            found_location = False
            location_links = driver.find_elements(By.CSS_SELECTOR, "a.yosegi-FilterPill-dropdownListItemLink")
            for loc in location_links:
                try:
                    if config['location'].lower() in loc.text.strip().lower():
                        driver.execute_script("arguments[0].scrollIntoView(true);", loc)
                        time.sleep(1)
                        loc.click()
                        logging.info(f"Selected Location filter: {loc.text.strip()}")
                        found_location = True
                        break
                except StaleElementReferenceException:
                    continue
            if not found_location:
                logging.warning(f"Location '{config['location']}' not found in available options.")
        except Exception as e:
            logging.warning(f"Location filter error: {e}")

        # --- Initialize Seen Links Set ---
        seen_links = set()

        # --- Scroll and Extract Easily Apply Jobs Across Pages ---
        # Clear file once at start
        with open(config['output_file'], 'w', encoding='utf-8') as f:
            pass

        while True:
            job_cards = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
            )

            for job in job_cards:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'})", job)
                    time.sleep(0.3)
                    easily_apply = job.find_element(By.XPATH, ".//span[contains(text(), 'Easily apply')]")
                    link_elem = job.find_element(By.CSS_SELECTOR, "a[data-hide-spinner]")
                    job_url = link_elem.get_attribute("href")
                    if job_url and job_url not in seen_links:
                        seen_links.add(job_url)
                        with open(config['output_file'], 'a', encoding='utf-8') as f:
                            f.write(job_url + "\n")
                except:
                    continue

            logging.info(f"Links collected so far: {len(seen_links)}")

            
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, window.innerHeight / 3);")
                time.sleep(0.5)

            
            try:
                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-testid='pagination-page-next']"))
                )
                next_btn_href = next_btn.get_attribute("href")
                if next_btn_href:
                    next_btn.click()
                    logging.info("Clicked on Next page button")
                    time.sleep(3)
                else:
                    logging.info("No more next page button. Ending pagination.")
                    break
            except:
                logging.info("No more next page button. Ending pagination.")
                break

        logging.info(f"Final number of links written to file: {len(seen_links)}")

    except Exception as e:
        logging.error(f"Job search failed: {str(e)}")
        raise

def extract_easily_apply_links(driver):
    time.sleep(3)
    links = set()
    cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
    for card in cards:
        try:
            if "Easily apply" in card.text:
                link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                if link:
                    links.add(link)
        except Exception:
            continue
    logging.info(f"Extracted {len(links)} easily apply links")
    return list(links)

def main():
    launch_debug_chrome()
    driver = attach_to_chrome()
    search_jobs(driver)
    links = extract_easily_apply_links(driver)
    with open(config["output_file"], "a") as f:
        f.write("\n".join(links))
    logging.info(f"Wrote {len(links)} links to {config['output_file']}")

if __name__ == "__main__":
    main()
