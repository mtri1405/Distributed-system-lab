import subprocess
from client.base import BasePlugin

class CPUPlugin(BasePlugin):
    def initialize(self, config):
        pass

    def run(self):
        # Lệnh: top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8}'
        cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'"
        try:
            return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        except:
            return "0.0"

    def finalize(self):
        pass

class RAMPlugin(BasePlugin):
    def initialize(self, config):
        pass

    def run(self):
        # Lệnh: free | awk '/Mem:/ {printf("%.2f", $3/$2*100)}'
        cmd = "free | awk '/Mem:/ {printf(\"%.2f\", $3/$2*100)}'"
        try:
            return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        except:
            return "0.0"

    def finalize(self):
        pass