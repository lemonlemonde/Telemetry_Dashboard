
import logging
import threading

from pynput import keyboard
    
from utils import MetricQueue

# non-blocking thread
def start_keyboard_listener(stop_event: threading.Event, queue: MetricQueue):
    logger = logging.getLogger(__name__)
    logger.info("Starting keyboard listener! 🎹")
    num_keys = 0
    
    # https://pynput.readthedocs.io/en/latest/keyboard.html
    def on_press(key):
        nonlocal num_keys
        
        try:
            # logger.info('{0} pressed (alphanumeric)'.format(
                # key.char))
            num_keys += 1
        except AttributeError:
            # logger.info('{0} pressed (special)'.format(
                # key))
            num_keys += 1

    def on_release(key):
        pass
        
    # start listener
    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release)
    listener.start()
    
    # time every minute for KPM
    while not stop_event.is_set():
        num_keys = 0
        stopped_early = stop_event.wait(timeout=60)
        if stopped_early:
            break
        logger.info(f'KPM: {num_keys}')
        # non blocking insert bc we want every 60 secs
        queue.put(num_keys)
            
        
    # close out at stop event
    listener.stop()
    listener.join()
    
    logger.info("Stopping keyboard listener! 🎹")
    