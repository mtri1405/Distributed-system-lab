import time
import json
import threading
import socket
import grpc
import etcd3
import subprocess 
import protos.monitor_pb2 as monitor_pb2
import protos.monitor_pb2_grpc as monitor_pb2_grpc
from client.plugin_manager import PluginManager

# --- CẤU HÌNH ---
MASTER_IP = '192.168.134.130' 
ETCD_PORT = 32379 
GRPC_PORT = 50051 

HOSTNAME = socket.gethostname()

# --- KHỞI TẠO ---
config_lock = threading.Lock()
current_config = {
    "interval": 5,
    "plugins": ["client.plugins.CPUPlugin", "client.plugins.RAMPlugin"]
}
plugin_manager = PluginManager()

# Hàng đợi để chứa kết quả lệnh cần gửi về Server
metric_queue = []
queue_lock = threading.Lock()

def etcd_heartbeat():
    """Gửi heartbeat lên etcd"""
    print(f"[Heartbeat] Starting heartbeat to {MASTER_IP}:{ETCD_PORT}...")
    try:
        etcd = etcd3.client(host=MASTER_IP, port=ETCD_PORT)
        key = f"/monitor/heartbeat/{HOSTNAME}"
        lease = etcd.lease(10)
        while True:
            etcd.put(key, "alive", lease=lease)
            lease.refresh()
            time.sleep(5)
    except Exception as e:
        print(f"[Heartbeat Error] {e}")

def etcd_watch():
    """Lắng nghe config"""
    print(f"[Watch] Listening for config at /monitor/config/{HOSTNAME}")
    try:
        etcd = etcd3.client(host=MASTER_IP, port=ETCD_PORT)
        key = f"/monitor/config/{HOSTNAME}"
        
        def callback(event):
            global current_config
            try:
                if isinstance(event.events[0], etcd3.events.PutEvent):
                    new_val = event.events[0].value.decode('utf-8')
                    new_conf = json.loads(new_val)
                    with config_lock:
                        current_config.update(new_conf)
                        plugin_manager.load_plugins(current_config["plugins"])
                    print(f"[Config Update] New config: {current_config}")
            except: pass

        etcd.add_watch_callback(key, callback)
        while True: time.sleep(10)
    except Exception as e:
        print(f"[Watch Error] {e}")

def execute_command(cmd_string):
    """Hàm thực thi lệnh Shell thực tế"""
    print(f"[Executing] {cmd_string}")
    try:
        # shell=True cho phép dùng pipe |, awk, grep...
        result = subprocess.check_output(cmd_string, shell=True, stderr=subprocess.STDOUT)
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return f"Error code {e.returncode}: {e.output.decode('utf-8')}"
    except Exception as e:
        return f"System Error: {e}"

def metrics_generator():
    """Hàm sinh dữ liệu gửi đi (Vừa gửi Metric định kỳ, vừa trả lời lệnh)"""
    last_metric_time = 0
    
    while True:
        current_time = time.time()
        
        # 1. Lấy config hiện tại
        with config_lock:
            interval = current_config.get("interval", 5)
        
        # 2. Kiểm tra xem đã đến lúc gửi Metric định kỳ chưa (CPU/RAM)
        if current_time - last_metric_time >= interval:
            plugins = plugin_manager.get_plugins()
            for p in plugins:
                val = p.run()
                yield monitor_pb2.MetricData(
                    hostname=HOSTNAME,
                    metric_type=p.__class__.__name__,
                    value=str(val),
                    timestamp=time.time()
                )
            last_metric_time = current_time

        # 3. Kiểm tra xem có kết quả lệnh nào đang chờ gửi không (Ưu tiên gửi ngay)
        # --- ĐÂY LÀ PHẦN QUAN TRỌNG BẠN THIẾU TRONG CODE CŨ ---
        with queue_lock:
            if metric_queue:
                while metric_queue:
                    # Lấy kết quả ra khỏi hàng đợi và gửi đi
                    yield metric_queue.pop(0)
        
        # Ngủ ngắn (0.5s) để vòng lặp phản hồi nhanh với lệnh mới
        time.sleep(0.5)

def run():
    plugin_manager.load_plugins(current_config["plugins"])
    
    # Bật lại các luồng etcd nếu đã test kết nối xong
    threading.Thread(target=etcd_heartbeat, daemon=True).start()
    threading.Thread(target=etcd_watch, daemon=True).start()

    server_address = f'{MASTER_IP}:{GRPC_PORT}'
    print(f"[gRPC] Connecting to Master at {server_address}...")
    
    channel = grpc.insecure_channel(server_address)
    stub = monitor_pb2_grpc.MonitorServiceStub(channel)

    try:
        # Gửi stream dữ liệu lên và nhận stream lệnh về
        responses = stub.CommandStream(metrics_generator())
        
        # Vòng lặp lắng nghe lệnh từ Server
        for resp in responses:
            cmd = resp.command
            if cmd:
                # 1. Thực thi lệnh thật sự (ĐÃ SỬA)
                output = execute_command(cmd)
                
                # 2. Đóng gói kết quả (ĐÃ SỬA)
                result_metric = monitor_pb2.MetricData(
                    hostname=HOSTNAME,
                    metric_type="CommandResult", # Đánh dấu đây là kết quả lệnh
                    value=output,
                    timestamp=time.time()
                )
                
                # 3. Đưa vào hàng đợi để metrics_generator gửi đi (ĐÃ SỬA)
                with queue_lock:
                    metric_queue.append(result_metric)
            
    except grpc.RpcError as e:
        print(f"[gRPC Disconnected] Server might be down. Error: {e}")
    except KeyboardInterrupt:
        print("Agent stopping...")

if __name__ == "__main__":
    run()