import threading
import json
import sys
import uuid
from kafka import KafkaConsumer, KafkaProducer

# Cấu hình
KAFKA_BOOTSTRAP = 'localhost:9092'
TOPIC_DATA = 'monitoring-data'
TOPIC_CMD = 'control-commands'

def consume_data_loop():
    """Luồng 1: Đọc và hiển thị Metric từ Worker"""
    try:
        consumer = KafkaConsumer(
            TOPIC_DATA,
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            auto_offset_reset='latest', # Chỉ đọc dữ liệu mới nhất
            group_id=f'analysis-viewer-{uuid.uuid4()}',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print("[Analysis] Listening for metrics...")
        for msg in consumer:
            val = msg.value
            # In ra màn hình nhưng cố gắng không làm vỡ giao diện nhập liệu
            # (Dữ liệu sẽ trôi lên trên dòng nhập lệnh)
            sys.stdout.write(f"\r[Metric] {val['host']} | {val['type']}: {val['val']}\nCMD> ")
            sys.stdout.flush()
    except Exception as e:
        print(f"[Consumer Error] {e}")

def produce_command_loop():
    """Luồng 2: Nhập lệnh và gửi vào Kafka"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            value_serializer=lambda x: json.dumps(x).encode('utf-8')
        )
        print("\n--- ANALYSIS COMMAND CENTER ---")
        print("Syntax: <target> <command>")
        print("Example: worker1 free -m")
        print("Example: all echo Hello")
        print("-------------------------------")

        while True:
            # Nhập lệnh từ bàn phím
            user_input = input("CMD> ").strip()
            if not user_input: continue

            parts = user_input.split(' ', 1)
            if len(parts) < 2:
                print("[!] Invalid syntax")
                continue
            
            command_packet = {
                "target": parts[0],
                "command": parts[1]
            }
            
            # Gửi lệnh
            producer.send(TOPIC_CMD, value=command_packet)
            
            # QUAN TRỌNG: Đẩy dữ liệu đi ngay lập tức
            producer.flush() 
            
            print(f"[Sent] {command_packet}")

    except Exception as e:
        print(f"[Producer Error] {e}")

if __name__ == "__main__":
    # Chạy Consumer ngầm
    t_consumer = threading.Thread(target=consume_data_loop, daemon=True)
    t_consumer.start()

    # Chạy Producer (Input) ở luồng chính
    produce_command_loop()