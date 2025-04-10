import subprocess
import time
import socket
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

def is_port_in_use(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(1)
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

def wait_for_port(port, host='127.0.0.1', timeout=60):
    start_time = time.time()
    while True:
        if is_port_in_use(port, host):
            return True
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timed out waiting for port {port}")
        time.sleep(2)

def launch_debug_chrome():
    chrome_path = config["chrome_executable_path"]
    user_data_dir = r"C:\Users\hr\AppData\Local\Google\Chrome\User Data"
    port = config['remote_debugging_port']

    if is_port_in_use(port):
        logging.info(f"Port {port} already in use.")
        return

    subprocess.Popen([
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--profile-directory=Profile 2",
        "--start-maximized",
        "about:blank"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    wait_for_port(port)
    logging.info("Chrome launched with debugging enabled.")

def attach_to_chrome():
    port = config['remote_debugging_port']
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    return webdriver.Chrome(options=options)
