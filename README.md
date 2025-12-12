## How the fuck lab 4 work 
# Required 1 master - 2 workers
# Required 6 terminals
# Step 1: Terminal 1
kubectl port-forward pod/kafka-1 -n kafka 9092:9092 --address 0.0.0.0   

# Step 2: Terminal 2 - Server

source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m server.server

# Step 3: Terminal 3 Analysis App
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m analysis.app

# Step 4: Terminal 4 Monitor hearbeat check
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m server.monitor

# Step 5: Active Worker For Both Worker1 and Worker2
source $HOME/dissys/bin/activate
cd ./DistSysMonitor/
python3 -m client.agent

# Step 6: Config
## Send info faster

# Worker1 Sending command per 1s Changing speed in {'interval': 1} <--- this one
python3 -c "import etcd3, json; etcd3.client(host='localhost', port=32379).put('/monitor/config/worker1', json.dumps({'interval': 1}))" 

# Super Fast Mother Fucker Worker2 Sending Command per 0.5s
python3 -c "import etcd3, json; etcd3.client(host='localhost', port=32379).put('/monitor/config/worker2', json.dumps({'interval': 0.5}))" 


## Optional for error 
# Find PID that use PORT
sudo lsof -i :<PORT>
sudo lsof -i :9092
sudo lsof -i :50051
# KILL PID 
sudo kill -9 <PID>
sudo kill -9 180761