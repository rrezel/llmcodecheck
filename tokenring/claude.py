from enum import Enum
import time
import threading
from typing import List, Set, Optional
import queue
import random

class MessageType(Enum):
    TOKEN = "TOKEN"
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    TOKEN_REQUEST = "TOKEN_REQUEST"
    TOKEN_REGENERATE = "TOKEN_REGENERATE"

class Message:
    def __init__(self, msg_type: MessageType, sender: int, 
                 receiver: int, token_id: Optional[int] = None):
        self.type = msg_type
        self.sender = sender
        self.receiver = receiver
        self.token_id = token_id
        self.timestamp = time.time()

class Process:
    def __init__(self, pid: int, n_processes: int):
        self.pid = pid
        self.n_processes = n_processes
        self.next_pid = (pid + 1) % n_processes
        self.has_token = False
        self.token_id = 0 if pid == 0 else None
        self.alive = True
        self.last_heartbeat: dict[int, float] = {i: time.time() for i in range(n_processes)}
        self.message_queue = queue.Queue()
        self.suspected_failed: Set[int] = set()
        self.requesting_token = False
        self.token_requests: List[int] = []
        
        # For formal verification
        self.critical_section = False
        self.token_holders = set()
        
        # Start heartbeat and message processing threads
        threading.Thread(target=self._heartbeat_thread).start()
        threading.Thread(target=self._process_messages).start()

    def request_token(self):
        """Request access to critical section"""
        self.requesting_token = True
        if not self.has_token:
            self._broadcast(MessageType.TOKEN_REQUEST, self.pid)

    def release_token(self):
        """Release the token and pass it to the next process"""
        if self.has_token:
            self.has_token = False
            self.critical_section = False
            next_pid = self._get_next_alive_process()
            if next_pid is not None:
                self._send_message(MessageType.TOKEN, next_pid, self.token_id)

    def _get_next_alive_process(self) -> Optional[int]:
        """Get the next alive process in the ring"""
        for i in range(self.n_processes):
            next_pid = (self.pid + i + 1) % self.n_processes
            if next_pid not in self.suspected_failed:
                return next_pid
        return None

    def _heartbeat_thread(self):
        """Periodically send heartbeats and check for failures"""
        while self.alive:
            # Send heartbeat to all processes
            self._broadcast(MessageType.HEARTBEAT, None)
            
            # Check for failed processes
            current_time = time.time()
            for pid in range(self.n_processes):
                if pid != self.pid:
                    if (current_time - self.last_heartbeat[pid] > 5.0 and 
                        pid not in self.suspected_failed):
                        self.suspected_failed.add(pid)
                        # If token holder failed, initiate token regeneration
                        if self.has_token and pid == self._get_next_alive_process():
                            self._broadcast(MessageType.TOKEN_REGENERATE, self.token_id)
            
            time.sleep(1)

    def _process_messages(self):
        """Process incoming messages"""
        while self.alive:
            try:
                message = self.message_queue.get(timeout=1)
                
                if message.type == MessageType.TOKEN:
                    self._handle_token(message)
                elif message.type == MessageType.HEARTBEAT:
                    self._handle_heartbeat(message)
                elif message.type == MessageType.HEARTBEAT_ACK:
                    self._handle_heartbeat_ack(message)
                elif message.type == MessageType.TOKEN_REQUEST:
                    self._handle_token_request(message)
                elif message.type == MessageType.TOKEN_REGENERATE:
                    self._handle_token_regenerate(message)
                
            except queue.Empty:
                continue

    def _handle_token(self, message: Message):
        """Handle receiving the token"""
        self.has_token = True
        self.token_id = message.token_id
        self.critical_section = True
        self.requesting_token = False
        
        # For formal verification
        self.token_holders.add(self.pid)
        
        # If there are pending requests, process them
        if self.token_requests:
            next_pid = self.token_requests.pop(0)
            if next_pid not in self.suspected_failed:
                self.release_token()

    def _handle_heartbeat(self, message: Message):
        """Handle heartbeat messages"""
        self._send_message(MessageType.HEARTBEAT_ACK, message.sender, None)

    def _handle_heartbeat_ack(self, message: Message):
        """Handle heartbeat acknowledgments"""
        self.last_heartbeat[message.sender] = time.time()
        if message.sender in self.suspected_failed:
            self.suspected_failed.remove(message.sender)

    def _handle_token_request(self, message: Message):
        """Handle token requests"""
        if message.sender not in self.token_requests:
            self.token_requests.append(message.sender)
        
        if self.has_token and not self.requesting_token:
            self.release_token()

    def _handle_token_regenerate(self, message: Message):
        """Handle token regeneration messages"""
        # Only regenerate if we have the highest alive PID
        highest_alive = max(pid for pid in range(self.n_processes) 
                          if pid not in self.suspected_failed)
        
        if self.pid == highest_alive:
            self.has_token = True
            self.token_id = message.token_id + 1
            self.release_token()

    def _send_message(self, msg_type: MessageType, receiver: int, 
                     token_id: Optional[int] = None):
        """Send a message to a specific process"""
        message = Message(msg_type, self.pid, receiver, token_id)
        # In a real implementation, this would use network communication
        # For simulation, we directly add to the receiver's queue
        if receiver not in self.suspected_failed:
            processes[receiver].message_queue.put(message)

    def _broadcast(self, msg_type: MessageType, token_id: Optional[int]):
        """Broadcast a message to all processes"""
        for pid in range(self.n_processes):
            if pid != self.pid and pid not in self.suspected_failed:
                self._send_message(msg_type, pid, token_id)

# Global process list for simulation
processes: List[Process] = []

def simulate_distributed_system(n: int):
    """Initialize and simulate the distributed system"""
    global processes
    processes = [Process(i, n) for i in range(n)]
    return processes