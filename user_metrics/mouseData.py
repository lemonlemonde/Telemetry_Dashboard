from pynput import mouse
import math
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

def start_mouse_listener(stop_event):
    
    num_clicks = 0
    
    prev_time = datetime.now(timezone.utc)
    prev_coords = (0, 0)
    speed_avg = 0
    num_secs = 0
    
    def on_move(x, y):
        nonlocal prev_coords, prev_time, num_secs, speed_avg
        
        now_time = datetime.now(timezone.utc)
        if (now_time - prev_time) >= timedelta(0, 1, 0):
            # 1 sec timer to calc dist
            prev_time = now_time
            
            dist_move = math.sqrt(((prev_coords[0] - x)** 2) + ((prev_coords[1] - y) ** 2))
            prev_coords = (x, y)
            
            # recalc avg
            speed_avg = ((speed_avg * num_secs) + dist_move) / (num_secs + 1)
            num_secs += 1
        
            logger.info(f'[{now_time}] : Avg speed: {speed_avg}')
            
        

    def on_click(x, y, button, pressed):
        nonlocal num_clicks
        
        num_clicks += 1
        
        logger.info('{0} at {1}'.format(
            'Pressed' if pressed else 'Released',
            (x, y)))

    def on_scroll(x, y, dx, dy):
        pass
        # print('Scrolled {0} at {1}'.format(
            # 'down' if dy < 0 else 'up',
            # (x, y)))

    # non blocking start
    listener = mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll)
    listener.start()

    # time every minute for clicks per min
    while not stop_event.is_set():
        num_clicks = 0
        # wait 60 seconds for CPM
        stopped_early = stop_event.wait(timeout=60)
        if stopped_early:
            break
        logger.info(f'CPM: {num_clicks}')
    
    # close out at stop_event
    logger.info("Closing out mouse listener.")
    listener.stop()
    listener.join()