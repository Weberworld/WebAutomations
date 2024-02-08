class Settings:
    HEADLESS = False

    TIMEOUT: int = 60

    SUNO_BASE_URL = "https://app.suno.ai/"
    NO_OF_TRACKS_SUNO_ACCOUNT_GENERATES = 2

    SOUND_CLOUD_BASE_URL = "https://soundcloud.com/"
    SOUND_CLOUD_ARTIST_BASE_URL = "https://artists.soundcloud.com/"

    # No of process to run concurrently
    CONCURRENT_PROCESS = 6

    MAX_RETRY = 3

    # No of secs to wait for a suno track to be ready for download
    MAX_TIME_FOR_SUNO_GENERATION = 120
