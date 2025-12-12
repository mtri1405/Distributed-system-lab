Hiểu rồi, bạn muốn một file hoàn chỉnh bao gồm cả **lời dẫn giải thích** (để người đọc hiểu context) và **khung code** (để copy chạy lệnh) nằm tách biệt nhau rõ ràng.

Dưới đây là nội dung **nguyên bản (Raw Markdown)**. Bạn hãy bấm nút **Copy** ở góc phải của khung bên dưới, sau đó dán (paste) toàn bộ vào file `README.md` của bạn.

Khi hiển thị trên GitHub, nó sẽ tự động chia thành văn bản và khung code riêng biệt rất đẹp.

````markdown
# Distributed Systems Monitor (Lab 4)

This repository contains the source code for a distributed system monitoring application. The system consists of a central server, an analysis service, a heartbeat monitor, and agents running on worker nodes.

## System Architecture
- **Infrastructure**: 1 Master Node, 2 Worker Nodes.
- **Dependencies**: Python 3, Kubernetes (Kafka), Etcd.
- **Environment**: All Python scripts assume the virtual environment is located at `$HOME/dissys/`.

## Deployment Guide

To deploy the full system, you will need approximately **6 terminal windows**.

### Step 1: Infrastructure Setup (Terminal 1)
First, you need to expose the Kafka service to the local network so components can communicate.

```bash
kubectl port-forward pod/kafka-1 -n kafka 9092:9092 --address 0.0.0.0
````

### Step 2: Start Central Services (Master Node)

Run the following components in separate terminals on the Master node.

**Terminal 2: Main Server**
Start the central gRPC server to handle requests.

```bash
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m server.server
```

**Terminal 3: Analysis App**
Start the analysis service to process metrics.

```bash
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m analysis.app
```

**Terminal 4: Heartbeat Monitor**
Start the monitor service to check worker availability.

```bash
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m server.monitor
```

### Step 3: Start Agents (Worker Nodes)

Run the agent script on **both** Worker 1 and Worker 2 to start sending metrics.

**Terminal 5 & 6 (On Workers)**

```bash
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m client.agent
```

-----

## Dynamic Configuration

You can update the reporting interval of the workers dynamically using `etcd`. Run the following commands in any terminal with access to the `dissys` environment.

**Set Worker 1 to Standard Speed (1s interval):**

```bash
python3 -c "import etcd3, json; etcd3.client(host='localhost', port=32379).put('/monitor/config/worker1', json.dumps({'interval': 1}))"
```

**Set Worker 2 to High-Frequency Mode (0.5s interval):**

```bash
python3 -c "import etcd3, json; etcd3.client(host='localhost', port=32379).put('/monitor/config/worker2', json.dumps({'interval': 0.5}))"
```

-----

## Troubleshooting

### Port Conflicts

If you encounter "Address already in use" errors, check for processes holding the required ports (9092, 50051, etc.).

**Find the Process ID (PID):**

```bash
sudo lsof -i :9092
# or
sudo lsof -i :50051
```

**Terminate the Process:**

```bash
sudo kill -9 <PID>
```

```
```
