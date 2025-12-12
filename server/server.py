import grpc
import threading
import queue
import json
import uuid
import time
from concurrent import futures
from kafka import KafkaProducer, KafkaConsumer
import protos.monitor_pb2 as monitor_pb2
import protos.monitor_pb2_grpc as monitor_pb2_grpc

# Cấu hình
KAFKA_BOOTSTRAP = 'localhost:9092' 
TOPIC_DATA = 'monitoring-data'
TOPIC_CMD = 'control-commands'

client_queues = {}
queues_lock = threading.Lock()

class MonitorService(monitor_pb2_grpc.MonitorServiceServicer):
    def __init__(self):
        self.producer = None
        self.producer_connected = False
        
        # --- CƠ CHẾ COOLDOWN (QUAN TRỌNG) ---
        self.last_retry_time = 0 
        self.RETRY_COOLDOWN = 5  # Chờ 5 giây mới được kết nối lại
        # ------------------------------------

    def get_producer(self):
        # 1. Nếu đang kết nối tốt -> Trả về luôn
        if self.producer_connected:
            return self.producer
        
        # 2. Nếu chưa kết nối, kiểm tra xem đã đủ thời gian chờ chưa
        current_time = time.time()
        if (current_time - self.last_retry_time) < self.RETRY_COOLDOWN:
            return None # Chưa đủ 5s, bỏ qua, không spam port

        # 3. Thử kết nối lại
        try:
            self.last_retry_time = current_time # Cập nhật thời gian thử
            self.producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BOOTSTRAP],
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                api_version_auto_timeout_ms=1000, # Timeout nhanh (1s)
                request_timeout_ms=1000
            )
            self.producer_connected = True
            print("[Kafka] Producer Re-connected.")
            return self.producer
        except:
            return None

    def CommandStream(self, request_iterator, context):
        client_id = "Unknown"
        try:
            for metric in request_iterator:
                client_id = metric.hostname
                
                # Đăng ký Queue
                with queues_lock:
                    if client_id not in client_queues:
                        client_queues[client_id] = queue.Queue()
                        print(f"[+] Client '{client_id}' registered.")

                # Xử lý Metric
                prod = self.get_producer() # Dùng hàm get_producer thông minh
                if prod:
                    try:
                        data = {
                            "host": client_id, 
                            "type": metric.metric_type, 
                            "val": metric.value,
                            "time": metric.timestamp
                        }
                        prod.send(TOPIC_DATA, value=data)
                        print(f"da nhan")
                        if metric.metric_type == "CommandResult":
                            print(f">>> Forwarded result from {client_id} to Kafka.")
                    except:
                        self.producer_connected = False # Đánh dấu lỗi để lần sau thử lại
                
                # Gửi lệnh chờ
                
                try:
                    cmd_to_send = client_queues[client_id].get_nowait()
                    print(f"thu goi lenh cho")
                    yield monitor_pb2.CommandRequest(command=cmd_to_send, args="")
                    print(f"dang cho")
                except queue.Empty:
                    pass
        except Exception as e:
            print(f"[Connection Error] Client {client_id} disconnected.")

def kafka_command_listener():
    print(f"[Kafka Listener] Watching topic '{TOPIC_CMD}'...")
    while True:
        try:
            consumer = KafkaConsumer(
                TOPIC_CMD,
                bootstrap_servers=[KAFKA_BOOTSTRAP],
                auto_offset_reset='earliest', 
                group_id=f'server-listener-{uuid.uuid4()}', 
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                request_timeout_ms=2000
            )
            
            for msg in consumer:
                cmd_data = msg.value 
                target = cmd_data.get('target')
                command = cmd_data.get('command')
                print(f"[Cmd Received] {target} : {command}")

                with queues_lock:
                    if target == "all":
                        for q in client_queues.values(): q.put(command)
                    elif target in client_queues:
                        client_queues[target].put(command)
        except Exception as e:
            time.sleep(5) # Chờ 5s nếu Listener lỗi

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    monitor_pb2_grpc.add_MonitorServiceServicer_to_server(MonitorService(), server)
    server.add_insecure_port('[::]:50051')
    
    threading.Thread(target=kafka_command_listener, daemon=True).start()

    print("gRPC Server started on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()