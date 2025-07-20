
from datetime import datetime, timezone
import time

import sys
import os
import threading
import logging
file_dir_path = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(
	    filename=file_dir_path + '/../' + 'logs/metrics.log',
	    level=logging.INFO,
	    format='[ %(asctime)s ] [%(levelname)s] [%(name)s] - %(message)s',
	    datefmt='%Y-%m-%d %H:%M:%S'
	)
logger = logging.getLogger("metrics")

import keyboardData as keyboardData
import mouseData as mouseData
import mediaData as mediaData

from utils import MetricQueue

import grpc

# for a gRPC logging bug on macOS
# https://github.com/grpc/grpc/issues/37642
os.environ["GRPC_VERBOSITY"] = "NONE"
from concurrent import futures



# for protobuf bug
# https://github.com/grpc/grpc/issues/29459
def add_to_python_path(new_path):
    existing_path = sys.path
    absolute_path = os.path.abspath(new_path)
    if absolute_path not in existing_path:
        sys.path.append(absolute_path)
    return sys.path

add_to_python_path(file_dir_path + "/proto")

from proto import metrics_pb2
from proto import metrics_pb2_grpc




# global metrics queues before sending via gRPC stream
# metrics:
# - keys per minute (KPM)
# - avg mouse speed (pixel dist / sec) (px/s)
# - clicks per minute (CPM)
# - list of active media/song titles every 30 seconds ()
kpm_queue = MetricQueue('kpm_queue')
mouse_speed_queue = MetricQueue('mouse_speed_queue')
cpm_queue = MetricQueue('cpm_queue')
media_queue = MetricQueue('media_queue')

# global stop event
stop_event = threading.Event()

def start_metrics():
    logger.info(f'✨✨ Metrics server started! ✨✨')
    
    # don't care for clean exits
    keyboard_thread = threading.Thread(
        target=keyboardData.start_keyboard_listener,
        args=(stop_event, kpm_queue),
        daemon=True
    )
    mouse_thread = threading.Thread(
        target=mouseData.start_mouse_listener,
        args=(stop_event, mouse_speed_queue, cpm_queue),
        daemon=True
    )
    media_thread = threading.Thread(
        target=mediaData.start_media_listener,
        args=(stop_event, media_queue),
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
    
    logger.info(f'✨✨ Metrics server stopped! ✨✨')
    
    

# implement the actual service
class MetricService(metrics_pb2_grpc.MetricServiceServicer):
    # implement the actual rpc streams
    # NOTE: when stopping this service,
        # gracefully, will take up to 20 seconds (due to sleeps)
        # nongracefully, doesn't matter
    
    # keys per minute
    def GetKPMStream(self, request, context):
        while context.is_active():
            # nonblocking to continuously check active client
            metric_tuple = kpm_queue.get()
            if metric_tuple != None:
                val, timestamp = metric_tuple
                yield metrics_pb2.MetricResponse(kpm=val, timestamp=timestamp)
            else:
                # sleep for a bit
                # it'll be max 60 seconds until new message
                time.sleep(20)

    
    # pixels per second
    def GetMouseSpeedStream(self, request, context):
        while context.is_active():
            # nonblocking to continuously check active client
            metric_tuple = mouse_speed_queue.get()
            if metric_tuple != None:
                val, timestamp = metric_tuple
                yield metrics_pb2.MetricResponse(pxm=val, timestamp=timestamp)
            else:
                # sleep for a bit
                time.sleep(0.5)
    
    # clicks per minute
    def GetCPMStream(self, request, context):
        while context.is_active():
            # nonblocking to continuously check active client
            metric_tuple = cpm_queue.get()
            if metric_tuple != None:
                val, timestamp = metric_tuple
                yield metrics_pb2.MetricResponse(cpm=val, timestamp=timestamp)
            else:
                # sleep for a bit
                time.sleep(20)
    
    # active media every 30 sec
    def GetMediaStream(self, request, context):
        while context.is_active():
            # nonblocking to continuously check active client
            metric_tuple = media_queue.get()
            if metric_tuple != None:
                val, timestamp = metric_tuple
                yield metrics_pb2.MetricResponse(title=val, timestamp=timestamp)
            else:
                # sleep for a bit
                time.sleep(10)
    
    
    
def start_server():
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # add the implemented service to the server
    metrics_pb2_grpc.add_MetricServiceServicer_to_server(MetricService(), server)
    
    # [::] = IPv6 shortcut for 0.0.0.0, every network interface
    server.add_insecure_port('[::]:50052')
    
    # start!
    server.start()
    logger.info("✨✨ gRPC server started on port 50052 ✨✨")
    
    
    # it says experimental API....but no documentation on what is better practice
        # wait why does this say NotImplementedError()??
        # https://grpc.github.io/grpc/python/_modules/grpc.html
        # my grpcio says i have 1.73.0 version
        # wait but this says that it returns stuff
            # https://grpc.github.io/grpc/python/grpc.html#grpc.Server.wait_for_termination
    # server.wait_for_termination()
    
    # use global stop event
    stop_event.wait()
    
    server.stop(grace=None)
    logger.info("✨✨ gRPC server stopped! ✨✨")
    
if __name__ == '__main__':
    logger.info("✨✨ ---- Main thread start! ---- ✨✨")
    server_thread = threading.Thread(target=start_server)
    metrics_thread = threading.Thread(target=start_metrics)
    
    server_thread.start()
    print("Grace period for gRPC server to start...")
    time.sleep(2)
    print("Grace period over!")
    metrics_thread.start()
    
    metrics_thread.join()
    server_thread.join()
    
    print("📐 Remaining queue sizes:")
    print(f"\t🎹 kpm_queue size: {kpm_queue.get_len()}")
    print(f"\t🐭 mouse_speed_queue size: {mouse_speed_queue.get_len()}")
    print(f"\t✅ cpm_queue size: {cpm_queue.get_len()}")
    print(f"\t🎶 media_queue size: {media_queue.get_len()}")
    
    logger.info("✨✨ ---- Main thread stop! ---- ✨✨")