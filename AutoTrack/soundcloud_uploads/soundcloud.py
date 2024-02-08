import os.path
import time
import pyperclip
import traceback

from selenium.webdriver import Keys
from selenium.common import ElementClickInterceptedException, JavascriptException, NoSuchElementException, TimeoutException

from WebAutomations.AutoTrack.helpers import handle_exception, wait_for_elements_presence, wait_for_elements_to_be_clickable
from WebAutomations.AutoTrack.settings import Settings
from WebAutomations.AutoTrack.utils import sign_in_with_google, get_all_downloaded_audios, save_cookies, load_cookies

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


SOUND_CLOUD_BASE_URL = "https://api.soundcloud.com/"


class SoundCloud:

    def __init__(self, driver):
        self.driver = driver
        self.result = {
            "account": "",
            "upload_count": 0,
            "monetization_count": 0
        }

    # Login into soundcloud
    def login(self, link, username, password, retry=Settings.MAX_RETRY):
        """
        Log in to soundcloud account using Google credentials
        :param link: A soundcloud redirect link with client_id, request_type data
        :param username: Account username
        :param password: Account password
        :param retry: Number of attempts to retry login in case of failure
        """
        # Vérifier si le nombre d'essais est positif
        if retry > 0:
            self.result['account'] = username

            try:
                print(f"Logging in to Soundcloud with: {username}\n")

                # Check if a cookie file exists for the account username
                account_cookie_file_path = f"cookies/soundcloud/{username}.pkl"
                if os.path.exists(account_cookie_file_path):
                    # Open the upload page
                    self.driver.uc_open("https://soundcloud.com/upload")
                    # Load the cookies
                    load_cookies(self.driver, "soundcloud", username)
                    # Wait a bit for the cookies to become active
                    self.driver.sleep(5)
                    # Check login with cookies is successful by checking for the presence of the sign-in button
                    logged_out = self.driver.execute_script("return (document.querySelector('.loginButton'))")
                    if not logged_out:
                        print("Login Success with cookies")
                        return
                    else:
                        # delete the cookies file
                        os.remove(account_cookie_file_path)

                # Ouvrir le lien de redirection de SoundCloud
                self.driver.uc_open(link)


                # Cliquer sur le bouton de connexion avec Google
                google_sign_option = wait_for_elements_to_be_clickable(self.driver,
                                                                       "div.provider-buttons > div > button.google-plus-signin.sc-button-google")[
                    0]

                google_sign_option.click()
                # Attendre que l'URL de la page ne soit plus celle de SoundCloud
                WebDriverWait(self.driver, Settings.TIMEOUT).until_not(
                    EC.url_matches(f"^{SOUND_CLOUD_BASE_URL}"))

                # Procéder à la connexion avec Google
                sign_in_with_google(self.driver, username, password)

                # Attendre que l'URL de la page corresponde à l'URL de base de SoundCloud + overview
                WebDriverWait(self.driver, Settings.TIMEOUT).until(
                    EC.url_matches(f"^{Settings.SOUND_CLOUD_ARTIST_BASE_URL}+overview"))
                print("Login success !\n")

                # Accepter les cookies
                try:
                    self.driver.click_if_visible(
                        "#onetrust-accept-btn-handler", timeout=Settings.TIMEOUT)
                    print("Accepted cookies !\n")


                except ElementClickInterceptedException:
                    # Gérer le cas où le bouton est intercepté
                    # Utiliser JavaScript pour cliquer sur le bouton
                    button = self.driver.execute_script(
                        "return document.getElementById('onetrust-accept-btn-handler');")
                    self.driver.execute_script("arguments[0].click();", button)

                except TimeoutException:
                    print("Cannot find cookies\n")
                    pass

            except Exception as e:
                # En cas d'exception, afficher le message d'erreur et réessayer avec un essai en moins
                print(
                    f"Unable to login {username}. Error: {e}. Retrying ...\n")
                return self.login(link, username, password, (retry - 1))
        else:
            # Si le nombre d'essais est nul ou négatif, fermer le navigateur et sortir de la fonction
            print(
                f"Failed to login {username} after {Settings.MAX_RETRY} attempts.\n")
            self.driver.quit()
            return

    def log_out(self):
        """
        Logs out from a logged in soundcloud account
        """
        # Clicks on the menu option
        wait_for_elements_to_be_clickable(
            self.driver, "#headlessui-menu-button-6")[0].click()
        # Click on the sign-out button
        wait_for_elements_to_be_clickable(
            self.driver, "#headlessui-menu-item-11")[0].click()
        # Wait for timeout until the log-out is completed
        sec_waited_for = 0
        while self.driver.current_url == Settings.SOUND_CLOUD_ARTIST_BASE_URL and sec_waited_for < Settings.TIMEOUT:
            time.sleep(1)

    @handle_exception(retry=True)
    def upload_tracks(self, downloaded_audios_info: list):
        """
        Upload downloaded tracks from suno_ai_spider run to the given to the artist profile
        """
        # Select the choose file to upload btn
        selected_audios = get_all_downloaded_audios()

        if len(selected_audios) == 0:
            print("No tracks to upload.")
            return

        self.driver.uc_open(
            Settings.SOUND_CLOUD_BASE_URL.replace("secure.", "") + "upload")

        # Dismiss if any pop up window shows up
        self.driver.sleep(2)
        self.driver.press_keys("button", Keys.ESCAPE)

        # Extract and save the cookies only if the cookie as not been set for the account
        if not os.path.exists(f"cookies/soundcloud/{self.result['account']}.pkl"):
            save_cookies(self.driver, "soundcloud", self.result['account'])

        # Click on not to create playlist
        self.driver.execute_script(
            'document.querySelector("input.sc-checkbox-input.sc-visuallyhidden").click()')
        self.driver.sleep(2)

        # Upload the audio files
        print("Uploading files")

        wait_for_elements_to_be_clickable(self.driver, "input.chooseFiles__input.sc-visuallyhidden")[0].send_keys(
            "\n".join(selected_audios))
        genre_name = downloaded_audios_info[0]['genre']
        print(f"Genre name is: {genre_name}")

        # Wait for all audio to upload
        print("Processing Uploads ... ")
        upload_status = self.driver.get_text(
            "span.uploadButton__title", timeout=Settings.TIMEOUT)
        while "processing" in upload_status.lower() or "uploading" in upload_status.lower():
            self.driver.sleep(1)
            upload_status = self.driver.get_text("span.uploadButton__title")
        print("Upload processing done")

        all_uploads_titles = wait_for_elements_presence(self.driver,
                                                        'div.baseFields__data > div.baseFields__title > div.textfield > div.textfield__inputWrapper > input')
        all_uploads_img = wait_for_elements_presence(
            self.driver, 'input.imageChooser__fileInput.sc-visuallyhidden')
        all_uploads_tags = wait_for_elements_presence(
            self.driver, 'input.tagInput__input.tokenInput__input')

        print("Filling Tracks upload form ...")
        for each in all_uploads_titles:
            for audio_info in downloaded_audios_info:
                if each.get_attribute("value").lower() == audio_info["title"].lower():
                    track_index = all_uploads_titles.index(each)
                    # Upload the track image
                    all_uploads_img[track_index].send_keys(
                        audio_info["img_path"])
                    # Set the additional tracks tags
                    # Convert the tag list to a string separated by spaces
                    tag_list_str = " ".join(audio_info["tag_list"])
                    # Copy the tag list string to the clipboard
                    pyperclip.copy(tag_list_str)
                    # Paste the tag list string from the clipboard
                    all_uploads_tags[track_index].send_keys(Keys.CONTROL, 'v')
                    self.driver.sleep(1)
                    break
        self.driver.execute_script(
            open("soundcloud_uploads/upload.js").read(), genre_name)
        print(f"{len(all_uploads_titles)} tracks has been uploaded")
        self.result['upload_count'] = len(all_uploads_img)
        # Wait for all tracks to get uploaded
        self.driver.sleep(30)

    def fill_monetization_form(self, btn_ele, no_of_retry=3):
        """ Fills the monetization form for a track and retry for the no_of_retry if a javascript error is raised"""
        self.driver.execute_script("arguments[0].click()", btn_ele)
        wait_for_elements_presence(self.driver, "#monetization-form")
        self.driver.sleep(1)
        fill_form_js_script = """
            let form_ele = document.getElementById("monetization-form");
            // Click on the content rating 
            form_ele.querySelector("div > div:nth-child(1) > div > label > div.mt-1 > div > div > button").click(); 
            // Get the content rating select list
            let content_rating_select_list_ele = form_ele.querySelector("div > div:nth-child(1) > div > label > div.mt-1 > div > ul");
            let rating_options = content_rating_select_list_ele.getElementsByTagName("li");
            // Loop through the rating options and select the Explicit option
            for (let i = 0; i < rating_options.length; i++) {
                if (rating_options[i].textContent == "Explicit") {
                    rating_options[i].click();
                    break;
                }
            }
            // In the songwriter options select "Another writer"
            form_ele.querySelector("div.mb-3 > div > div:nth-child(1) > div.flex > label > div.mt-1 > label:nth-child(2) > div > input").click();
            // Mark that you agree to the T/C
            form_ele.querySelector("div:nth-child(15) > div input").click()
            // Submit the form_ele
            form_ele.querySelector("div:nth-child(16) > button:nth-child(2)").click();
            // Click on the cancel btn
            form_ele.querySelector("div:nth-child(16) > button").click();
        """
        try:
            self.driver.execute_script(fill_form_js_script)
        except JavascriptException:
            # If this exception is raised. Re-run the function and execute the script again
            self.driver.execute_script("arguments[0].click()", btn_ele)
            if not no_of_retry <= 0:
                self.fill_monetization_form(btn_ele, (no_of_retry - 1))
            else:
                print("Retry exceeded")
        except NoSuchElementException:
            pass
        except Exception as e:
            print(e)

    def monetize_track(self, max_num_of_pages=3):
        """
        Monetize tracks on the account. Paginates to the next page if needed.
        """
        print("Monetizing Tracks ....")

        # Check if the account is allowed for monetization
        try:
            not_allowed_text = self.driver.get_text(
                "#right-before-content > div", timeout=Settings.TIMEOUT)
            if not_allowed_text == "You don't have access to this page.":
                return False
        except TimeoutException:
            pass

        self.driver.sleep(2)

        i = 1  # Counter for the number of monetized songs
        while max_num_of_pages > 0:
            # Get the monetization btn elements
            all_monetize_track_btns = self.driver.find_elements(
                By.XPATH, "//button[contains(text(), 'Monetize this track')]")

            print(
                f"Found {len(all_monetize_track_btns)} tracks to monetize on Page {4 - max_num_of_pages}")

            # Monetize tracks if available
            if all_monetize_track_btns:
                # Monetize all tracks on the current page
                for btn_ele in all_monetize_track_btns:
                    print(f"{i} monetized song...")
                    self.fill_monetization_form(btn_ele)
                    self.driver.sleep(2)
                    i += 1

            js_script = """
            var paginationButton = document.querySelector('button[aria-label="Go to next page"]');
            if (paginationButton) {
                paginationButton.scrollIntoView();
                paginationButton.click();
            }
            """
            try:
                # Execute JavaScript to scroll to and click the pagination button
                self.driver.execute_script(js_script)
                print(
                    f"Navigating to monetization next page - Page {3 - max_num_of_pages}")
                self.driver.sleep(7)
                max_num_of_pages -= 1
                continue
            except TimeoutException:
                print("No more pages to navigate.")
                break
            except Exception as e:
                print(f"Pagination button not found or not clickable: {e}")
                traceback.print_exc()  # print the full traceback
                break

        print(f"{i-1} tracks have been monetized")

    @handle_exception()
    def sync_soundcloud_tracks(self):
        """
        Navigates to soundcloud monetization and clicks on synchronize with soundcloud btn then wait for a minute
        :return:
        """
        print("Synchronizing ...")
        self.driver.get(Settings.SOUND_CLOUD_ARTIST_BASE_URL + "monetization")
        try:
            WebDriverWait(self.driver, timeout=Settings.TIMEOUT).until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Sync with SoundCloud')]")))
            sync_btn = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Sync with SoundCloud')]")

            self.driver.execute_script(
                "arguments[0].click()", sync_btn)
            print("Waiting for 3 minutes for soundcloud synchronization")
            self.driver.sleep(180)
            return True
        except (TimeoutException, IndexError):
            return False


def run_soundcloud_bot(driver, link, username, password, store, soundcloud_result: list):
    """
    Run the soundcloud action bot
    :@param driver: Seleniumbase webdriver object
    :param link: Authentication link from soundcloud
    :param username:  registered username
    :param password: Soundcloud password
    :param store: List of all downloaded tracks from suno AI bot
    :param soundcloud_result: List to store the result of the soundcloud bot run
    """
    # Vérifier si la liste des pistes à télécharger n'est pas vide
    if store:
        # Créer un objet SoundCloud avec le driver
        soundcloud_bot = SoundCloud(driver)
        # Essayer de se connecter, de télécharger les pistes, de les synchroniser et de les monétiser
        try:
            soundcloud_bot.login(link, username, password)
            soundcloud_bot.upload_tracks(store)
            if soundcloud_bot.sync_soundcloud_tracks():
                soundcloud_bot.driver.get(
                    Settings.SOUND_CLOUD_ARTIST_BASE_URL + "monetization")
                soundcloud_bot.monetize_track()
            # Ajouter le résultat à la liste soundcloud_result
            soundcloud_result.append(soundcloud_bot.result)
        # En cas d'exception, afficher l'erreur et la trace complète
        except Exception as e:
            print("Error on soundcloud.py : ", e)
            traceback.print_exc()
        # Fermer le driver
        finally:
            driver.quit()
    # Sinon, afficher un message indiquant qu'il n'y a pas de pistes à télécharger
    else:
        print("No Tracks to upload. ")
