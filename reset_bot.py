import requests
import time
import logging
import os
from typing import Optional

# ================= CONFIGURATION (from GitHub secrets) =================
BASE_URL = "https://start.cosmosss.online"
USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]
TARGET_USERNAMES = [u.strip() for u in os.environ["TARGET_USERNAMES"].split(",") if u.strip()]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
# ======================================================================

def login() -> Optional[str]:
    """Authenticate and return access token."""
    login_url = f"{BASE_URL}/api/admin/token"
    data = {"username": USERNAME, "password": PASSWORD}
    try:
        resp = session.post(login_url, data=data, timeout=10)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            if token:
                logger.info("Login successful, token obtained.")
                return token
            else:
                logger.error("Token not found in response.")
        else:
            logger.error(f"Login failed with status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Login request error: {e}")
    return None

def get_user_id(username: str, token: str) -> Optional[int]:
    """Search for user and return internal user ID."""
    url = f"{BASE_URL}/api/users"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"search": username}
    try:
        resp = session.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("users", [])
            for user in users:
                if user.get("username", "").lower() == username.lower():
                    user_id = user.get("id")
                    if user_id:
                        logger.info(f"Found user '{username}' with ID {user_id}")
                        return user_id
                    else:
                        logger.warning(f"User '{username}' found but no id field.")
            logger.warning(f"User '{username}' not found in search results.")
        else:
            logger.error(f"User search failed for '{username}': {resp.status_code}")
    except Exception as e:
        logger.error(f"Error searching for user '{username}': {e}")
    return None

def reset_hardware_ids(user_id: int, token: str, username: str) -> bool:
    """Send POST request to reset all hardware IDs for the given user."""
    url = f"{BASE_URL}/api/user/{user_id}/hwids/reset"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = session.post(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            logger.info(f"✅ Hardware IDs reset for '{username}' (ID {user_id})")
            return True
        else:
            logger.error(f"Reset failed for '{username}' (ID {user_id}) - status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Reset request error for '{username}': {e}")
    return False

def process_user(username: str, token: str) -> bool:
    """Get user ID and reset hardware IDs."""
    user_id = get_user_id(username, token)
    if user_id is None:
        return False
    return reset_hardware_ids(user_id, token, username)

def run_cycle():
    """One full cycle: login and reset all target usernames."""
    logger.info("========== Starting new reset cycle ==========")
    token = login()
    if not token:
        logger.error("Unable to obtain token. Skipping cycle.")
        return

    success_count = 0
    for username in TARGET_USERNAMES:
        if process_user(username, token):
            success_count += 1
        time.sleep(1)   # small delay between users

    logger.info(f"Cycle completed: {success_count}/{len(TARGET_USERNAMES)} successful resets.")
    logger.info("Cycle finished.\n")

if __name__ == "__main__":
    logger.info("Single reset cycle started.")
    run_cycle()