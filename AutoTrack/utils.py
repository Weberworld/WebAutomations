import os
import pickle
import time
from datetime import datetime
import requests
from settings import Settings
import re  # import the regular expression module


def parse_prompts() -> list:
    """
        Go through the suno_ao_music_genre_prompt txt file and get the genres names and prompts.
        Organize the data such that each item is a dictionary with the keys 'genre' and 'prompt'.
    """
    prompts = []  # create an empty list to store the prompts
    genre = None  # create a variable to store the current genre
    with open("suno_prompts.txt", "r") as file:  # open the file in read mode
        for line in file:  # loop through each line in the file
            line = line.strip()  # remove any leading or trailing whitespace
            if line.startswith("###"):  # check if the line is a genre name
                genre = line[4:]  # extract the genre name without the ###
            # check if the line is a prompt using a regular expression
            elif re.match(r"^\d+\.", line):
                # extract the prompt without the number and dot and remove any extra whitespace
                prompt = line.split(".", 1)[1].strip()
                # create a dictionary with the genre and prompt and append it to the list
                prompts.append({"genre": genre, "prompt": prompt})
    return prompts  # return the list of prompts


def get_available_platform_accounts_v2(account_type) -> list:
    """
    Get all platform credential that are stored on the virtual environment
    This assumes that the password is same for all platform account.

    :param account_type: (suno, soundcloud)
    """

    # Get environment variables that match the account type
    all_platform_username_environ_keys = [key for key in os.environ.keys() if
                                          key.startswith(account_type.upper() + "_USERNAME_")]

    # Get the password for the account type
    password = os.environ.get(account_type.upper() + "_PASSWORD")

    # Create a list of tuples with username and password
    all_accounts = []
    for username in all_platform_username_environ_keys:
        try:
            # Get the username value from the environment variable
            username_value = os.environ.get(username)
            # Append the tuple to the list
            all_accounts.append((username_value, password))
        except (AttributeError, ValueError):
            # Skip invalid or missing environment variables
            pass
    return all_accounts


def sign_in_with_microsoft(driver, username, password):
    """
        Sign in to Microsoft account using the username and password.
        This assumes the Microsoft account does not use device authentication
        :param driver: Webdriver object
        :param username: Account username
        :param password: Account password

    """
    print("Signing in with microsoft...\n")
    driver.type("#i0116", username, timeout=Settings.TIMEOUT)
    driver.click_if_visible("#idSIButton9")

    # Type password
    driver.type("#i0118", password, timeout=Settings.TIMEOUT)
    driver.click_if_visible("#idSIButton9")
    if re.search(f"^{Settings.SUNO_BASE_URL}", driver.current_url):
        return

    try:
        driver.click("#acceptButton", timeout=30)
    except Exception as e:
        pass
        # print(e)
        # print("Cannot find #idBtn_Back")
        # Incase the id changes
        # driver.click("#declineButton")


def sign_in_with_google(driver, username, password):
    """
    Sign in to a Google account using the username and password.
    This assumes the Google account uses device authentication
    :param driver: Webdriver object
    :param username: Account username
    :param password: Account password

    """
    driver.type("input#identifierId", username, timeout=Settings.TIMEOUT)

    driver.click_if_visible(
        "div#identifierNext > div > button", timeout=Settings.TIMEOUT)

    # Type password
    driver.type("div#password > div > div > div > input",
                password, timeout=Settings.TIMEOUT)
    driver.click_if_visible(
        "#passwordNext > div > button", timeout=Settings.TIMEOUT)

    driver.sleep(3)


def download_image(link, image_name):
    """
    Downloads an image from link and store it into the downloaded_files folder
    :param image_name: Name to store the image with
    :param link: link to download the image
    :return: Returns the path to the image location
    """

    # Define the path to the images folder
    images_path = "downloaded_files/images/"

    # Check if the images folder exists, if not create it
    if not os.path.exists(images_path):
        os.makedirs(images_path)

    # Open the image file in write binary mode
    with open(images_path + image_name + ".png", mode="wb") as handle:
        res = requests.get(link, stream=True)

        for block in res.iter_content(1024):
            if not block:
                break
            handle.write(block)
    return os.path.join(os.getcwd(), f"{images_path + image_name}.png")


def get_all_downloaded_audios() -> list:
    """
    Returns a list of all downloaded audio paths from a suno download session
    :return:
    """

    download_dir = os.path.join(os.getcwd(), "downloaded_files")
    all_downloaded_audio_files_path = [os.path.join(download_dir, audio_file) for audio_file in os.listdir(download_dir)
                                       if
                                       os.path.isfile(os.path.join(download_dir, audio_file))]
    return all_downloaded_audio_files_path


def delete_downloaded_files():
    """
    Deletes all downloaded files from a run session
    :return:
    """
    track_dir = os.path.join(os.getcwd(), "downloaded_files")
    img_dir = os.path.join(os.getcwd(), "downloaded_files/images")

    for file_path in os.listdir(track_dir):
        abs_file_path = os.path.join(track_dir, file_path)
        if os.path.isfile(abs_file_path) and file_path != "driver_fixing.lock":
            os.remove(abs_file_path)

    for img_path in os.listdir(img_dir):
        abs_img_path = os.path.join(img_dir, img_path)
        if os.path.isfile(abs_img_path) and img_path != "driver_fixing.lock":
            os.remove(abs_img_path)


def delete_uploaded_files(all_uploads_file_info):
    """
    Deletes all uploaded audios and images
    @param all_uploads_file_info: List of the suno downloads results
    """
    track_dir = "downloaded_files/"
    images_dir = "downloaded_files/images/"

    for each in all_uploads_file_info:
        file_path = track_dir + each['title'] + ".mp3"
        img_path = images_dir + each['title'] + ".png"
        if os.path.exists(file_path):
            os.remove(os.path.join(os.getcwd(), file_path))
        if os.path.exists(img_path):
            os.remove(img_path)


def send_telegram_message(message: str):
    """
    Sends a message to a telegram account
    :param message: Message to send
    """
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&parse_mode=HTML&text={message}'
        # Sends the message
        requests.get(url)
    except Exception:
        pass


def send_daily_statistics(no_of_tracks_downloaded: int, no_of_all_suno_accounts: int, genre: str,
                          result_from_soundcloud: list):
    """
    Send a statistical telegram report of daily process routine
    :param no_of_tracks_downloaded: Number of all downloaded tracks  info
    :param no_of_all_suno_accounts: Number of all available suno accounts
    :param genre: Genre name used
    :param result_from_soundcloud: List of all result the soundcloud bot returns
    :return:
    """
    date = datetime.now().date().strftime("%d/%m/%Y")

    telegram_message = f"🎶 <b>Résumé de la production musicale - <i>{date}</i></b> 🎶\n\n"
    telegram_message += f"🌐 <b>Statistiques globales - Comptes Suno AI</b>\n\n"
    telegram_message += f"— Genre utilisé : <i>{genre}</i>\n"
    telegram_message += f"— Chansons créées : <i>{no_of_tracks_downloaded}</i>/<i>{no_of_all_suno_accounts * 10}</i> attendues\n"
    telegram_message += f"— Comptes Suno AI utilisés : <i>{no_of_all_suno_accounts}</i>\n\n"
    telegram_message += f"📝 <b>Détails par compte SoundCloud</b>\n\n"

    # Créer un dictionnaire qui stocke les résultats par compte SoundCloud
    results_by_account = {}
    for upload_details in result_from_soundcloud:
        account = upload_details['account']
        if account not in results_by_account:
            # Initialiser le dictionnaire pour ce compte
            results_by_account[account] = {
                'upload_count': 0,
                'monetization_count': 0
            }
        # Ajouter les résultats de cette session au dictionnaire
        results_by_account[account]['upload_count'] += upload_details['upload_count']
        results_by_account[account]['monetization_count'] += upload_details['monetization_count']

    # Parcourir le dictionnaire pour créer le message Telegram
    for index, (account, results) in enumerate(results_by_account.items(), start=1):
        telegram_message += f"🔹 Compte SoundCloud <i>{index}</i> - <i>{account}</i>\n"
        telegram_message += f"— Chansons téléversées : <i>{results['upload_count']}</i>/<i>{no_of_all_suno_accounts * 10}</i> attendues\n"
        telegram_message += f"— Chansons monétisées : <i>{results['monetization_count']}</i>\n"
        if index < len(results_by_account):
            telegram_message += f"——————————————————————————\n"
    send_telegram_message(telegram_message)


def scroll_down(driver):
    # Get scroll height.
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to the bottom.
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        # Wait to load the page.
        time.sleep(2)
        # Calculate new scroll height and compare with last scroll height.
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def save_cookies(driver, platform, account_id):
    """
    Save the cookies from a website. The cookies will be stored in this format: /cookies/platform/account_id.pkl
    :param driver: seleniumbase webdriver object
    :param platform: website name. suno / soundcloud
    :param account_id: Username of the logged-in user.
    """

    platform_cookie_dir = f"cookies/{platform}/"

    # Create the platform cookie directory if it does not exist
    if not os.path.exists(platform_cookie_dir):
        os.makedirs(platform_cookie_dir)

    print("Getting cookies ...")

    # Get all the available cookies on the platform
    cookies = driver.get_cookies()
    print(len(cookies))

    for cookie in cookies:
        try:
            # Set the domain to the root domain name of the website
            domain_name = ".soundcloud.com" if platform == "soundcloud" else ".suno.ai"
            cookie['domain'] = domain_name
            driver.add_cookie(cookie)
        except TypeError:
            pass

    # Save the extracted cookies to platform with its account_id as the file name
    pickle.dump(cookies, open(f"{platform_cookie_dir}{account_id}.pkl", "wb"))
    print(f"Cookies saved {platform_cookie_dir}{account_id}.pkl")


def load_cookies(driver, platform, account_id):
    """
    Loads cookies from a saved account_id.pkl file to the website
    :param driver: seleniumbase webdriver object
    :param platform: website name. suno / soundcloud
    :param account_id: Account username.

    """
    # Compute the account cookies path
    account_cookie_path = f"cookies/{platform}/{account_id}.pkl"

    # Try to load cookie from account cookie path
    try:
        cookies = pickle.load(open(account_cookie_path, "rb"))
        print(f"Loading cookies for account {platform} account: {account_id}")
        for cookie in cookies:
            cookie['domain'] = ".suno.ai"
            driver.add_cookie(cookie)
            print(cookie)

        # Refresh the page after cookies has been added
        print("Loaded cookies!!!")
        driver.refresh()
        return True

    except (FileExistsError, FileNotFoundError) as e:
        print(e)
        # Cookies has not been saved for the given account_id
        print("No set cookie for the given account")
        return False
