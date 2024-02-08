"""
This is to be run only on local testing
"""

import os
import time
from threading import Thread
from settings import Settings
from helpers import create_driver
from utils import parse_prompts, get_available_platform_accounts_v2, delete_downloaded_files, send_daily_statistics
from WebAutomations.AutoTrack.soundcloud_uploads.soundcloud import run_soundcloud_bot
from sunodownloads.suno_ai_spider import run_suno_bot
from dotenv import load_dotenv
import datetime  # import the datetime module to get the current date
import random  # import the random module
import traceback  # import the traceback module

# Charger les variables d'environnement
load_dotenv()

print("Started !\n")

# Définir une fonction qui exécute le processus d'automatisation


def automation_process():
    # Initialiser le nombre total de téléchargements à zéro
    no_of_all_downloads = 0
    # Obtenir la liste des comptes disponibles pour Suno et Soundcloud
    all_suno_accounts = get_available_platform_accounts_v2("suno")
    all_soundcloud_account = get_available_platform_accounts_v2("soundcloud")
    # Créer une liste vide pour stocker les résultats de Soundcloud
    result_from_soundcloud = list()
    print(f"Got {len(all_suno_accounts)} Suno accounts\n")
    print(f"Got {len(all_soundcloud_account)} Soundcloud accounts\n")

    # Obtenir la liste des invites quotidiens à utiliser pour chaque genre
    all_daily_prompts = parse_prompts()

    # Obtenir le jour actuel du mois
    today = datetime.date.today()
    day = today.day

    # Obtenir le nom du genre à utiliser en fonction du jour et du nombre de genres
    # Utiliser le modulo pour boucler si le jour est supérieur au nombre de genres
    genre_names = sorted(set(prompt["genre"] for prompt in all_daily_prompts))
    num_genres = len(genre_names)
    genre_index = (day - 1) % num_genres
    genre_used = genre_names[genre_index]

    # Filtrer la liste des invites par le nom du genre
    all_daily_prompts = [
        prompt for prompt in all_daily_prompts if prompt["genre"] == genre_used]

    # Créer un dictionnaire qui contient une liste d'invites aléatoires pour chaque thread Suno
    selected_prompts = {}
    for j in range(len(all_suno_accounts)):
        key = f"\nSuno Thread {j + 1}"
        value = random.sample(all_daily_prompts, 5)
        selected_prompts[key] = value

    # Créer des index pour parcourir la liste des comptes Suno
    suno_start_index = 0
    suno_end_index = Settings.CONCURRENT_PROCESS
    # Créer une variable d'arrêt pour contrôler la boucle
    stop = False
    while not stop:
        # Créer une liste vide pour stocker les threads Suno
        all_suno_threads = []
        # Créer une liste vide pour stocker les informations sur les fichiers audio téléchargés
        all_downloaded_audios_info = list()
        # Parcourir la liste des comptes Suno par tranches de Settings.CONCURRENT_PROCESS
        for account in all_suno_accounts[suno_start_index:suno_end_index]:

            username = account[0]
            password = account[1]

            # Récupérer le nom du thread et la liste des invites correspondants
            thread_name = f"\nSuno Thread {(all_suno_accounts.index(account) + 1)}"
            thread_prompts = selected_prompts[thread_name]
            print(thread_prompts)

            # Créer un thread Suno qui exécute la fonction run_suno_bot avec les arguments appropriés
            suno_thread = Thread(name=thread_name,
                                 target=run_suno_bot,
                                 args=(create_driver(), username, password, thread_prompts,
                                       all_downloaded_audios_info))
            suno_thread.start()
            print(suno_thread.name + " started !\n")
            # Ajouter le thread à la liste des threads Suno
            all_suno_threads.append(suno_thread)
            time.sleep(2)
            break

        # Attendre que tous les threads Suno se terminent
        for suno_thread in all_suno_threads:
            suno_thread.join()

        # Mettre à jour le nombre total de téléchargements
        no_of_all_downloads += len(all_downloaded_audios_info)

        # Vérifier s'il y a des fichiers audio à télécharger
        if not all_downloaded_audios_info:
            # Créer des index pour parcourir la liste des comptes Soundcloud
            soundcloud_start_index = 0
            soundcloud_end_index = Settings.CONCURRENT_PROCESS
            while True:
                # Créer une liste vide pour stocker les threads Soundcloud
                all_soundcloud_threads = []
                # Parcourir la liste des comptes Soundcloud par tranches de Settings.CONCURRENT_PROCESS
                for account in all_soundcloud_account[soundcloud_start_index:soundcloud_end_index]:
                    # Créer une instance de bot Soundcloud
                    username = account[0]
                    password = account[1]

                    driver = create_driver()

                    # Créer un thread Soundcloud qui exécute la fonction run_soundcloud_bot avec les arguments appropriés
                    soundcloud_thread = Thread(name=f"\nSoundcloud account: {username}", target=run_soundcloud_bot,
                                               args=(driver, os.getenv("SOUNDCLOUD_LINK"), username, password,
                                                     all_downloaded_audios_info, result_from_soundcloud)
                                               )
                    soundcloud_thread.start()
                    print(soundcloud_thread.name + " started !\n")
                    # Ajouter le thread à la liste des threads Soundcloud
                    all_soundcloud_threads.append(soundcloud_thread)
                    time.sleep(2)
                    break

                # Attendre que tous les threads Soundcloud se terminent
                for soundcloud_thread in all_soundcloud_threads:
                    soundcloud_thread.join()

                # Vérifier si on a atteint la fin de la liste des comptes Soundcloud
                if soundcloud_end_index >= len(all_soundcloud_account):
                    break
                # Sinon, incrémenter les index de départ et de fin
                soundcloud_start_index = soundcloud_end_index
                soundcloud_end_index += Settings.CONCURRENT_PROCESS

        # Supprimer les fichiers téléchargés
        delete_downloaded_files()

        # Vérifier si on a atteint la fin de la liste des comptes Suno
        if suno_end_index >= len(all_suno_accounts):
            # Mettre la variable d'arrêt à True pour arrêter la boucle
            stop = True
        else:
            # Sinon, incrémenter les index de départ et de fin
            suno_start_index = suno_end_index
            suno_end_index += Settings.CONCURRENT_PROCESS

    print("\nSending Message...")
    # Envoyer le rapport statistique pour le processus de la journée entière
    # Fusionner les résultats de Soundcloud par compte
    merged_soundcloud_result = []
    for result in result_from_soundcloud:
        for each in merged_soundcloud_result:
            if result["account"] == each["account"]:
                result["upload_count"] += each["upload_count"]
                result["monetization_count"] += each["monetization_count"]
                merged_soundcloud_result.remove(each)

        merged_soundcloud_result.append(result)

    send_daily_statistics(no_of_all_downloads, len(
        all_suno_accounts), genre_used, merged_soundcloud_result)

    print("\nDone !\n")


# Exécuter la fonction d'automatisation
try:
    automation_process()
except Exception as e:
    print("\nError on main.py : ", e)
    traceback.print_exc()  # print the full traceback
