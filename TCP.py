import queue
import socket
import json
import threading
import random

TTL = None


class TCPHeader():
    def __init__(self, SYN=None, FIN=None, ACK=None, SEQ=None, SEQACK=None, LEN=None, CHECKSUM=None, PAYLOAD=None)  -> None:
        self.SYN = SYN
        self.FIN = FIN
        self.ACK = ACK
        self.SEQ = SEQ
        self.SEQACK = SEQACK
        self.LEN = LEN
        self.CHECKSUM = CHECKSUM
        self.PAYLOAD = PAYLOAD

    def to_bytes(self):
        json_data =  {
            "SYN": self.SYN,
            "FIN": self.FIN,
            "ACK": self.ACK,
            "SEQ": self.SEQ.to_bytes(4, 'big').hex(),  
            "SEQACK": self.SEQACK.to_bytes(4, 'big').hex() if self.SEQACK is not None else None,
            "LEN": self.LEN,
            "CHECKSUM": self.CHECKSUM,
            "PAYLOAD": self.PAYLOAD if isinstance(self.PAYLOAD, str) else self.PAYLOAD.hex() if self.PAYLOAD else None
        }

        return json.dumps(json_data).encode()
    
    def from_bytes(self, data):
        data = json.loads(data)
        self.SYN = data["SYN"]
        self.FIN = data['FIN']
        self.ACK = data['ACK']
        self.SEQ = int.from_bytes(bytes.fromhex(data["SEQ"]), 'big') if data["SEQ"] else None
        self.SEQACK = int.from_bytes(bytes.fromhex(data["SEQACK"]), 'big') if data["SEQACK"] else None,
        self.LEN = data['LEN']
        self.CHECKSUM = data['CHECKSUM']
        self.PAYLOAD = data['PAYLOAD']

        return self



class ByteBuffer():
    def __init__(self, max_size = 212992, max_read = 1024):
        self.max_size = max_size
        self.max_read = max_read
        self.queue = queue.Queue()
        self.current_size = 0 
        self.cond = threading.Condition() 
    
    def add_data(self, data):
        with self.cond:
            if not isinstance(data, bytes):
                raise ValueError("Data must be of type bytes.")
        
            data_length = len(data)
            if self.current_size + data_length > self.max_size:

                allowable_size = self.max_size - self.current_size

            if allowable_size > 0:
                data = data[:allowable_size]
                self.queue.put(data)
                self.current_size += allowable_size
                self.cond.notify_all()

            else:
                self.queue.put(data)
                self.current_size += data_length
                self.cond.notify_all()

    def read_data(self, length=None):
        with self.cond:
            if length is None or length > self.max_read:
                length = self.max_read

            data_read = bytes()
            while length > 0:
                while self.queue.empty():
                    self.cond.wait()

                data_chunk = self.queue.get()
                if len(data_chunk) <= length:
                    data_read += data_chunk
                    length -= len(data_chunk)
                    self.current_size -= len(data_chunk)
                else:
                    data_read += data_chunk[:length]
                    self.queue.put(data_chunk[length:])
                    self.current_size -= length
                    break
        return data_read




class TCPSocket():
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.SEQ =  None
        self._send_to = None
        self._recv_from = None
        self.connections = {}
        self.buffer = ByteBuffer()


    
    def handler(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            if addr not in self.connections:
                self.buffer.add_data(data, addr)
            else:
                self.connections[addr]['buffer'].add_data(data)

    def bind(self, address):
        self.udp_socket.bind(address)


    def accept(self):
        threading.Thread(target=self.handler, daemon=True).start()

        while True:
            data, addr = self.buffer.read_data(1024)
            header = TCPHeader().from_bytes(data)

            if header.SYN == 1 and header.ACK == 0:
                self.SEQ = random.randint(0, 0xFFFFFFFF)
                SEQACK = header.SEQ + 1
                response = TCPHeader(SYN=1, ACK=1, SEQ=self.SEQ ,SEQACK=SEQACK)
                
                buffer = ByteBuffer()
                self.connections[addr] = {'buffer': buffer, "socket": socket}

                socket = TCPSocket()
                socket.buffer = buffer
                socket.SEQ = self.SEQ
                socket._recv_from = addr
              
                socket.send(response)

               

    


    def connect(self,  address:(str, int)):
        SEQ = random.randint(0, 0xFFFFFFFF)
        header = TCPHeader(SYN=1, ACK=0, SEQ=SEQ, SEQACK=0)
        self._send_to = address

        self.send(header)

        data, addr =  self.recv()
        # data, addr = self.buffer.read_data(1024)
        header = TCPHeader().from_bytes(data)
        
        if header.SYN == 1 and header.ACK == 1:  # This is a SYN-ACK packet
            ack_header = TCPHeader(ACK=1)

    def recv(self):
        address = self._recv_from
        data = self.buffer.read_data()
        data = TCPHeader.from_bytes(data)

    


    def send(self, data):
        address = self._send_to
        self.udp_socket.sendto(data, address)
    

    def sendall():
        raise  NotImplementedError()


    def close():
        raise  NotImplementedError()




if __name__ == '__main__':
    port = 12345
    ip = "127.0.0.1"
    address = (ip, port)
    a = TCPSocket()



    a = TCPHeader()
    a.PAYLOAD = 'tesadasdas'
    
    buffer = ByteBuffer()
    print(buffer.read_data())
    buffer.add_data(a.to_bytes())
    
  
    # a.bind(address)


    # while True:
    #     client_socket, addr = a.accept()  
    #     print(f"Connected by {addr}")

        # while True:
        #     data = client_socket.recv(1024)
        #     if not data:
        #         break
        #     print(f"Received {data.decode()} from {addr}")
        #     client_socket.send(data)  # Echo back the received data

        # client_socket.close()  # 关闭连接
