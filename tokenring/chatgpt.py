import threading
import time
import random

class Process(threading.Thread):
    def __init__(self, process_id, ring, is_token_holder=False):
        super().__init__()
        self.process_id = process_id
        self.ring = ring
        self.is_token_holder = is_token_holder
        self.active = True

    def run(self):
        while self.active:
            time.sleep(random.uniform(1, 3))  # Simulate processing delay
            if self.is_token_holder:
                self.use_resource()
                self.pass_token()

    def use_resource(self):
        print(f"Process {self.process_id} is using the token.")
        time.sleep(random.uniform(1, 2))  # Simulate resource usage time

    def pass_token(self):
        next_process = self.ring.get_next_active(self.process_id)
        if next_process:
            print(f"Process {self.process_id} passing token to {next_process.process_id}")
            next_process.receive_token()
            self.is_token_holder = False

    def receive_token(self):
        if self.active:
            self.is_token_holder = True

    def fail(self):
        print(f"Process {self.process_id} has failed.")
        self.active = False
        self.is_token_holder = False

    def recover(self):
        print(f"Process {self.process_id} has recovered.")
        self.active = True

class TokenRing:
    def __init__(self, num_processes):
        self.processes = [Process(i, self, is_token_holder=(i == 0)) for i in range(num_processes)]

    def get_next_active(self, process_id):
        num_processes = len(self.processes)
        for i in range(1, num_processes):
            next_id = (process_id + i) % num_processes
            if self.processes[next_id].active:
                return self.processes[next_id]
        return None  # No active process found (should trigger token regeneration)

    def detect_and_regenerate_token(self):
        while True:
            time.sleep(5)  # Periodic failure check
            active_processes = [p for p in self.processes if p.active]
            if not any(p.is_token_holder for p in active_processes) and active_processes:
                print("No active token found. Regenerating token...")
                active_processes[0].receive_token()
                print(f"New token holder: Process {active_processes[0].process_id}")

    def start(self):
        for process in self.processes:
            process.start()
        threading.Thread(target=self.detect_and_regenerate_token, daemon=True).start()

# Example usage
if __name__ == "__main__":
    num_processes = 5
    ring = TokenRing(num_processes)
    ring.start()

    time.sleep(5)  # Allow processes to start working
    ring.processes[2].fail()  # Simulate failure of process 2
    time.sleep(10)
    ring.processes[2].recover()  # Simulate recovery of process 2
    time.sleep(20)
