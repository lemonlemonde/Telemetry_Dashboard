import subprocess
import logging
import threading

from utils import MetricQueue

def get_spotify_now_playing():
    script = '''
    tell application "Spotify"
        if player state is playing then
            set trackName to name of current track
            set artistName to artist of current track
            return trackName & " by " & artistName
        else
            return "No track playing"
        end if
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip()
    

def is_app_running(app_name):
    script = f'''
    tell application "System Events"
        return (name of processes) contains "{app_name}"
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip().lower() == "true"


def get_all_firefox_window_titles():
    # NOTE: Firefox doesn't support AppleScripting
    #   can only retrieve windows (active tab within each window)
    script = '''
    tell application "System Events"
        set window_list to name of every window of process "Firefox"
        return window_list
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    titles = result.stdout.strip().split(", ")
    return titles


def get_safari_tab_titles():
    script = '''
    tell application "Safari"
        set output to ""
        repeat with w in windows
            set window_name to name of w
            repeat with t in tabs of w
                set tab_name to name of t
                set output to output & window_name & " | " & tab_name & linefeed
            end repeat
        end repeat
        return output
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip().splitlines()


def get_chrome_tab_titles():
    script = '''
    tell application "Google Chrome"
        set output to ""
        repeat with w in windows
            set window_name to title of active tab of w
            repeat with t in tabs of w
                set tab_name to title of t
                set output to output & window_name & " | " & tab_name & linefeed
            end repeat
        end repeat
        return output
    end tell
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    return result.stdout.strip().splitlines()

def find_youtube_tabs():
    """
    Find tabs with "- youtube" in title in Firefox, Chrome, Safari
    Note limitations of Firefox.
    Note that it attempts to ignore the YouTube subscriptions page
        Specifically tried to prevent from ignoring bops like:
        https://www.youtube.com/watch?v=u9GV1XMbIWQ
    """
    titles = []
    
    if is_app_running('Firefox'):
        titles.extend(get_all_firefox_window_titles())
    if is_app_running('Safari'):
        titles.extend(get_safari_tab_titles())
    if is_app_running('Chrome'):
        titles.extend(get_chrome_tab_titles())
    
    yt_tabs = [title for title in titles if "subscriptions - youtube" != title.lower() and ") subscriptions - youtube" not in title.lower() and "- youtube" in title.lower()]
    
    return yt_tabs
    
def get_possible_media():
    titles = find_youtube_tabs()
    spotify_track = get_spotify_now_playing()
    if spotify_track != 'No track playing':
        titles.append(spotify_track)
    return titles
    
def start_media_listener(stop_event: threading.Event, queue: MetricQueue):
    logger = logging.getLogger(__name__)
    logger.info("Starting media listener! 🎶")
    while not stop_event.is_set():
        # check media every 30 seconds
        stop_event.wait(30)
        if stop_event.is_set():
            break
        titles = get_possible_media()
        logger.info(titles)
        for title in titles:
            queue.put(title)
    
    logger.info("Stopping media listener! 🎶")