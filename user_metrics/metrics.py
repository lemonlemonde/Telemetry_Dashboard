
import threading
import logging
logging.basicConfig(filename='logs/metrics.log', level=logging.INFO)

import user_metrics.keyboardData as keyboardData
import user_metrics.mouseData as mouseData

from datetime import datetime, timezone

def main():
    logger = logging.getLogger(__name__)
    
    # global stop event
    stop_event = threading.Event()
    
    time_str = datetime.now(timezone.utc)
    logger.info(f'[{time_str}] : ✨✨ Start! ✨✨')
    
    # don't care for clean exit
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
    keyboard_thread.start()
    mouse_thread.start()
    
    # wait until stop event
    stop_event.wait()
    
    time_str = datetime.now(timezone.utc)
    logger.info(f'[{time_str}] : ✨✨ Exit! ✨✨')
    
    
if __name__ == '__main__':
    main()