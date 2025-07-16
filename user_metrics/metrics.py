
import threading
import logging
logging.basicConfig(
	    filename='logs/metrics.log',
	    level=logging.INFO,
	    format='[ %(asctime)s ] [%(levelname)s] [%(name)s] - %(message)s',
	    datefmt='%Y-%m-%d %H:%M:%S'
	)

import keyboardData as keyboardData
import mouseData as mouseData
import mediaData as mediaData

from datetime import datetime, timezone

def main():
    logger = logging.getLogger("metrics")
    
    # global stop event
    stop_event = threading.Event()
    
    time_str = datetime.now(timezone.utc)
    logger.info(f'✨✨ Start! ✨✨')
    
    # don't care for clean exits
    keyboard_thread = threading.Thread(
        target=keyboardData.start_keyboard_listener,
        args=(stop_event,),
        daemon=True
    )
    mouse_thread = threading.Thread(
        target=mouseData.start_mouse_listener,
        args=(stop_event,),
        daemon=True
    )
    media_thread = threading.Thread(
        target=mediaData.start_media_listener,
        args=(stop_event,),
        daemon=True
    )
    keyboard_thread.start()
    mouse_thread.start()
    media_thread.start()
    
    # input is stop event
    input("Press ENTER to stop all listeners:")
    stop_event.set()
    
    # wait for all to join first, even if it's daemon..?
    keyboard_thread.join()
    mouse_thread.join()
    media_thread.join()
    
    logger.info(f'✨✨ Exit! ✨✨')
    
    
if __name__ == '__main__':
    main()