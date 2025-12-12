import etcd3
import time

# IP Master (localhost vì chạy trên master)
ETCD_HOST = 'localhost'
ETCD_PORT = 32379 # Port NodePort của etcd

def watch_nodes():
    print(f"--- HEARTBEAT MONITOR ---")
    print(f"Connecting to etcd at {ETCD_HOST}:{ETCD_PORT}...")
    
    try:
        etcd = etcd3.client(host=ETCD_HOST, port=ETCD_PORT)
        watch_key = "/monitor/heartbeat/"
        
        print("Waiting for heartbeats...")

        def event_handler(event):
            for e in event.events:
                key = e.key.decode('utf-8')
                node_name = key.split('/')[-1]
                
                if isinstance(e, etcd3.events.PutEvent):
                    # Client vừa gửi heartbeat hoặc khởi động
                    print(f"✅ [ONLINE] Node '{node_name}' is active.")
                elif isinstance(e, etcd3.events.DeleteEvent):
                    # Lease hết hạn (Client chết)
                    print(f"❌ [OFFLINE] Node '{node_name}' DIED!")

        etcd.add_watch_prefix_callback(watch_key, event_handler)

        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    watch_nodes()