import re
import os
from selenium.common import JavascriptException
from seleniumbase.common.exceptions import TimeoutException
import traceback 
from WebAutomations.AutoTrack.utils import sign_in_with_microsoft, scroll_down, save_cookies, load_cookies
from WebAutomations.AutoTrack.settings import Settings
from WebAutomations.AutoTrack.helpers import wait_for_elements_presence, handle_exception, wait_for_elements_to_be_clickable
import threading

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

lock = threading.Lock()

class SunoAI:
    def __init__(self, driver):
        """
        :param driver: Seleniumbase driver object
        """
        self.driver = driver
        self.driver.set_window_size(1920, 1080)

    def sign_in(self, username, password, max_retry=Settings.MAX_RETRY):
        """
            Opens the sign-in page on suno and signs in to an account using a Microsoft account credential.
                :param username: Account username
                :param password: Account password
                :param max_retry: Number of attempts to retry login in case of failure
        """
        if max_retry > 0:
            try:
                print(f"Starting Suno process for {username}\n")

                # Check if a cookie file exists for the account username
                account_cookie_file_path = f"cookies/suno/{username}.pkl"
                if os.path.exists(account_cookie_file_path):
                    # Open the create page
                    self.driver.get("https://app.suno.ai")
                    # Load the cookies
                    load_cookies(self.driver, "suno", username)
                    # Wait a bit for the cookies to become active

                    # Check login with cookies is successful by checking the page is not redirected to log in
                    if self.driver.current_url == Settings.SUNO_BASE_URL + "create":
                        print("Login Success with cookies")
                        return
                    else:
                        print("Expired cookies on suno login")
                        input()

                # Ouvrir la page de connexion de Suno
                self.driver.get(Settings.SUNO_BASE_URL)

                sign_up_btn = wait_for_elements_to_be_clickable(self.driver, "nav > div.css-7a2ne0 > div:nth-child(3) > button")[0]
                sign_up_btn.click()
                # Cliquer sur le bouton de connexion avec Microsoft
                WebDriverWait(self.driver, Settings.TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.cl-socialButtonsIconButton.cl-socialButtonsIconButton__microsoft"))).click()
                # Utiliser la fonction sign_in_with_microsoft pour se connecter avec les identifiants
                sign_in_with_microsoft(self.driver, username, password)
                # Attendre que l'URL de la page soit celle de la page d'accueil de Suno
                WebDriverWait(self.driver, Settings.TIMEOUT).until(
                    lambda driver: re.search(f"^{Settings.SUNO_BASE_URL}", driver.current_url))
                print("Login Success !\n")

                save_cookies(self.driver, "suno", username)

            except Exception as e:
                print(f"Unable to login {username}. Error: {e}. Retrying...\n")
                return self.sign_in(username, password, max_retry - 1)
        else:
            print(f"Failed to login {username} after {Settings.MAX_RETRY} attempts.\n")
            self.driver.quit()


    def sign_out(self):
        """
        Sign out from a logged in suno account
        """
        # Click on the menu option button
        wait_for_elements_to_be_clickable(
            self.driver, "button.cl-userButtonTrigger")[0].click()
        # Click sign out button
        wait_for_elements_to_be_clickable(
            self.driver, "button.cl-userButtonPopoverActionButton__signOut")[0].click()
        self.driver.sleep(3)

    def create_song(self, prompt):
        """
        Create a music on suno.ai using the given prompt as the track description
        :param prompt: Prompt to use to generate track lyrics
        """
        print("Creating tracks...\n")

        prompt_input_ele = "div.chakra-stack.css-131jemj > div.chakra-stack.css-10k728o > textarea"
        wait_for_elements_to_be_clickable(
            self.driver, prompt_input_ele)[0].clear()
        self.driver.type(prompt_input_ele, prompt, timeout=Settings.TIMEOUT)
        self.driver.click(
            "div.chakra-stack.css-10k728o > div > button.chakra-button")

    @handle_exception(retry=True)
    def get_generated_tracks_selection(self) -> list:
        """
        Get the option btns of the newly created tracks.
       """
        select_btns = wait_for_elements_presence(
            self.driver,
            "button.chakra-button.chakra-menu__menu-button.css-o244em")[-Settings.NO_OF_TRACKS_SUNO_ACCOUNT_GENERATES::]
        return select_btns

    def wait_for_new_track(self):
        """
        Wait for new generated tracks to be ready.
        When the tracks are ready, the images and the tags string will be ready
        """
        self.driver.sleep(2)
        secs_waited_for = 0
        while self.driver.execute_script(
                "return (document.querySelector('.chakra-spinner.css-12wh8ho'))") and secs_waited_for <= Settings.TIMEOUT:
            self.driver.sleep(1)
            secs_waited_for += 1
        self.driver.sleep(2)

    def wait_for_new_track_to_be_ready(self):
        """
        Wait for a set number of minutes until the track is ready for download
        """
        print(
            f"\nWaiting for track to be ready for download within {Settings.MAX_TIME_FOR_SUNO_GENERATION / 60} minutes ....\n")
        scroll_down(self.driver)
        max_wait_limit_in_secs = 0
        while max_wait_limit_in_secs < Settings.MAX_TIME_FOR_SUNO_GENERATION:
            if self.driver.execute_script(
                    "return (document.querySelector('div.css-yle5y0 > div > div > div > div > div > div > div > button.chakra-menu__menuitem > div.chakra-spinner'))"):
                self.driver.sleep(1)
                max_wait_limit_in_secs += 1
            else:
                break
        else:
            return False

        try:
            download_btns = wait_for_elements_to_be_clickable(self.driver,
                                                              "div.css-yle5y0 > div > div > div > div > div > div > div > button.chakra-menu__menuitem")
            # Check if the list is not empty
            if download_btns and download_btns[3].is_enabled():
                self.driver.execute_script(
                    "arguments[0].scrollIntoView();", download_btns[3])
            return True
        except TimeoutException:
            print(
                f"Track was not ready for download after {Settings.MAX_TIME_FOR_SUNO_GENERATION / 60} minutes")
            return False
        
    def run(self, account_username, all_prompt_info, store_into):
        """
        Use a list of prompts to generate track and suno and store the details (title, genre, tag_list) of the downloaded track
        to the store_into list variable.
        :param account_username: Logged in suno account username
        :param all_prompt_info: list of prompts to use to generate track on suno
        :param store_into: List to store the details of the downloaded track
        """
        # Définit le chemin vers le dossier des fichiers téléchargés
        # Utilise le chemin du script comme racine
        # dir_path = os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files")
        # # Vérifie si le dossier existe, sinon le crée
        # os.makedirs(dir_path, exist_ok=True)
        # # Définit le chemin vers le sous-dossier des images
        # images_path = os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files", "images")
        # # Vérifie si le sous-dossier existe, sinon le crée
        # os.makedirs(images_path, exist_ok=True)

        print("Opening the create track page...\n")

        # Tentative de chargement de la page avec gestion du délai d'expiration
        try:
            self.driver.set_page_load_timeout(Settings.TIMEOUT/2)
            self.driver.get(Settings.SUNO_BASE_URL + "create")
        except TimeoutException:
            print(
                "Le chargement de la page a pris trop de temps. Rafraîchissement de la page...")
            self.driver.refresh()

        # Extract and save the cookies
        save_cookies(self.driver, "suno", account_username)
        return

        for prompt in all_prompt_info:
            try:
                no_of_credit = self.driver.get_text(
                    ".chakra-text.css-itvw0n", timeout=Settings.TIMEOUT).split(" ")[0]
            except:
                self.driver.refresh()
                no_of_credit = self.driver.get_text(
                    ".chakra-text.css-itvw0n", timeout=Settings.TIMEOUT).split(" ")[0]

            if int(no_of_credit) < 10:
                print("\nNot enough credits.\n")
                self.driver.quit()
                return

            # Create tracks with a given prompt
            self.create_song(prompt["prompt"])
            self.wait_for_new_track()
            generated_tracks_sel_btn = self.get_generated_tracks_selection()
            # Check if the list is not empty
            if generated_tracks_sel_btn:
                index = 0
                for btn_ele in generated_tracks_sel_btn:
                    self.driver.execute_script(
                        "arguments[0].click();", btn_ele)

                    if not self.wait_for_new_track_to_be_ready():
                        # If the track is not ready for download. skip to the next track if available
                        try:
                            self.driver.execute_script(
                                "arguments[0].click()", btn_ele)
                        except JavascriptException:
                            pass
                        continue
                    scraped_details = self.scrap_details()

                    track_title: str = scraped_details[0][index].text

                    track_tags = scraped_details[1][index]
                    genre = prompt["genre"]
                    # Exécute le script JS pour obtenir l'attribut data-clip-id
                    data_clip_id = self.driver.execute_script(
                        """
                        // On récupère l'élément cliqué
                        let element = arguments[0];
                        // On initialise une variable pour stocker l'attribut data-clip-id
                        let dataClipId = null;
                        // On parcourt la chaîne hiérarchique ascendante jusqu'à la racine du document
                        while (element && element !== document) {
                        // On vérifie si l'élément courant a un attribut data-clip-id
                        if (element.hasAttribute("data-clip-id")) {
                            // On récupère la valeur de l'attribut data-clip-id
                            dataClipId = element.getAttribute("data-clip-id");
                            // On arrête la boucle
                            break;
                        }
                        // On passe à l'élément parent
                        element = element.parentNode;
                        }
                        // On retourne l'attribut data-clip-id
                        return dataClipId;
                        """, self.driver.find_element(By.CSS_SELECTOR,
                            "div.css-yle5y0 > div > div > div > div > div > div > div > button.chakra-menu__menuitem"))
                    # Construit l'URL du morceau à partir de l'attribut data-clip-id
                    song_url = f"https://cdn1.suno.ai/{data_clip_id}.mp3"
                    # Envoie une requête GET à l'URL du morceau et récupère la réponse
                    response = requests.get(song_url)
                    # Vérifie si le code de statut de la réponse est 200, ce qui signifie que la requête a réussi
                    if response.status_code == 200:
                        # Définit le nom du fichier du morceau avec l'extension mp3
                        song_file = f"{track_title}.mp3"
                        # Vérifie si le nom du fichier existe déjà dans le dossier
                        if os.path.exists(os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files", song_file)):
                            # Si oui, ajoute un suffixe ordinal au titre jusqu'à ce qu'il soit unique
                            i = 2
                            while os.path.exists(os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files", song_file)):
                                # Détermine le suffixe ordinal en fonction du nombre
                                if i % 10 == 1 and i != 11:
                                    ordinal = "st"
                                elif i % 10 == 2 and i != 12:
                                    ordinal = "nd"
                                elif i % 10 == 3 and i != 13:
                                    ordinal = "rd"
                                else:
                                    ordinal = "th"
                                # Génère le nouveau titre avec le suffixe ordinal
                                song_file = "{0} - {1}{2} version.mp3".format(
                                    track_title, i, ordinal)
                                i += 1
                        # Écrit le contenu de la réponse dans le fichier
                        with open(os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files", song_file), "wb") as f:
                            f.write(response.content)
                    else:
                        # Affiche un message d'erreur avec le code de statut de la réponse
                        print(f"Unable to download song. Status code: {response.status_code}")
                        return None
                    # Construit l'URL de l'image à partir de l'attribut data-clip-id
                    img_url = f"https://cdn1.suno.ai/image_{data_clip_id}.png"
                    # Envoie une requête GET à l'URL de l'image et récupère la réponse
                    res = requests.get(img_url)
                    # Vérifie si le code de statut de la réponse est 200, ce qui signifie que la requête a réussi
                    if res.status_code == 200:
                        # Définit le nom du fichier de l'image avec le même titre que le fichier audio
                        img_file = song_file.replace(".mp3", ".png")
                        # Écrit le contenu de la réponse dans le fichier
                        with open(os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files", "images", img_file), "wb") as handle:
                           
                            for block in res.iter_content(1024):
                                if not block:
                                    break
                                handle.write(block)
                        # Récupère le chemin complet du fichier image
                        img_path =os.path.join(os.getenv('CURRENT_DIR'), "downloaded_files", "images")
                        
                    else:
                        # Affiche un message d'erreur avec le code de statut de la réponse
                        print(f"Unable to download image. Status code: {res.status_code}")
                        img_path = ""

                    # Formate la liste des tags
                    tag_list = track_tags.text.split(" ")
                    # Stocke les informations du morceau dans un dictionnaire
                    track_details = {
                        "account": account_username,
                        "title": song_file.split(".")[0],
                        "genre": genre,
                        "tag_list": tag_list,
                        "img_path": img_path
                    }
                    print(track_details)
                    # Stocke les détails du morceau téléchargé
                    store_into.append(track_details)
                    index += 1
                    self.driver.sleep(5)
                self.driver.refresh()
                    
            else:
                print("No tracks generated")
                self.driver.quit()
                return


    @handle_exception()
    def scrap_details(self) -> tuple:
        """
        Scraps the webpage for track titles and genre names
        """
        all_titles = wait_for_elements_presence(self.driver, "p.chakra-text.css-1fq6tx5")[
            -Settings.NO_OF_TRACKS_SUNO_ACCOUNT_GENERATES::]
        all_genre_list = wait_for_elements_presence(self.driver, "p.chakra-text.css-1icp0bk")[
            -Settings.NO_OF_TRACKS_SUNO_ACCOUNT_GENERATES::]
        return all_titles, all_genre_list

    

def run_suno_bot(driver, username, password, prompt, store):
    """
    Runs the Suno Ai bot
    :param driver: Seleniumbase webdriver
    :param username: Microsoft username
    :param password: Microsoft password
    :param prompt: List of prompts to use to create tracks on Suno AI
    :param store: List to store all downloaded tracks info
    """
    try:
        suno_bot = SunoAI(driver)

        suno_bot.sign_in(username, password)
        suno_bot.run(username, prompt, store)
        suno_bot.driver.quit()

    except Exception as e:
        print("Error on suno_ai_spider.py : ", e)
        traceback.print_exc()  # print the full traceback
        driver.close()
