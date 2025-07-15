import time
import logging
import threading

from pynput import keyboard
    
logger = logging.getLogger(__name__)

# non-blocking thread
def start_keyboard_listener(stop_event: threading.Event):
    num_keys = 0
    
    # https://pynput.readthedocs.io/en/latest/keyboard.html
    def on_press(key):
        nonlocal num_keys
        
        try:
            logger.info('{0} pressed (alphanumeric)'.format(
                key.char))
            num_keys += 1
        except AttributeError:
            logger.info('{0} pressed (special)'.format(
                key))
            num_keys += 1

    def on_release(key):
        if key == keyboard.Key.esc:
            # TODO: Stop listener based on some other event
            stop_event.set()
            return False
        
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
        
    # close out at stop event
    logger.info("Closing out keyboard listener")
    listener.stop()
    listener.join()