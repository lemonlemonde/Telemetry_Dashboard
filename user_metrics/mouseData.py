import math
from datetime import datetime, timezone, timedelta
import threading

import logging
from pynput import mouse

from utils import MetricQueue

def start_mouse_listener(stop_event: threading.Event, mouse_speed_queue: MetricQueue, cpm_queue: MetricQueue):
    logger = logging.getLogger(__name__)
    logger.info("Starting mouse listener! 🐭")
    
    
    num_clicks = 0
    
    prev_time = datetime.now(timezone.utc)
    prev_coords = (0, 0)
    dist_move = 0
    
    num_secs = 0
    
    def on_move(x, y):
        nonlocal prev_coords, prev_time, num_secs, dist_move
        
        now_time = datetime.now(timezone.utc)
        if (now_time - prev_time) >= timedelta(milliseconds=500):
            # 0.5 sec timer to add to dist
            prev_time = now_time
            
            dist_move += math.sqrt(((prev_coords[0] - x)** 2) + ((prev_coords[1] - y) ** 2))
            prev_coords = (x, y)
        

    def on_click(x, y, button, pressed):
        nonlocal num_clicks
        
        num_clicks += 1
        
        # logger.info('{0} mouse'.format(
            # 'Pressed' if pressed else 'Released'))

    def on_scroll(x, y, dx, dy):
        pass
        # print('Scrolled {0} at {1}'.format(
            # 'down' if dy < 0 else 'up',
            # (x, y)))
            
            
    def start_click_listener():
        nonlocal num_clicks
        
        # time every minute for clicks per min
        while not stop_event.is_set():
            num_clicks = 0
            # wait 60 seconds for CPM
            stopped_early = stop_event.wait(timeout=60)
            if stopped_early:
                break
            logger.info(f'CPM: {num_clicks}')
            cpm_queue.put(num_clicks)
            
    def start_speed_listener():
        nonlocal dist_move
        
        # time every min for pixels/min
        while not stop_event.is_set():
            dist_move = 0
            # wait 60 sec for pixels/min
            stopped_early = stop_event.wait(timeout=60)
            if stopped_early:
                break
        
            logger.info(f'Pixels per min: {dist_move}')
            # non blocking insert bc not that important
            mouse_speed_queue.put(dist_move)
        
        

    # non blocking start
    listener = mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll)
    listener.start()

    click_thread = threading.Thread(target=start_click_listener)
    speed_thread = threading.Thread(target=start_speed_listener)
    
    click_thread.start()
    speed_thread.start()
    
    # click and speed threads will exit with stop_event
    click_thread.join()
    speed_thread.join()
    
    # close out at stop_event
    listener.stop()
    listener.join()
    
    logger.info("Stoppin mouse listener! 🐭")