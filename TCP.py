import queue
import socket
import json
import threading
import random
import time
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
        self.TTL = None
        self.table = {}
        self.recv_data = ByteBuffer()
        threading.Thread(target=self.handler, daemon=True).start()

    
    def buffer_handler(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            if addr not in self.connections:
                self.buffer.add_data(data, addr)
            else:
                self.connections[addr]['buffer'].add_data(data, addr)



    def bind(self, address):
        self.udp_socket.bind(address)


    def accept(self):
        threading.Thread(target=self.buffer_handler, daemon=True).start()

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
        result = ""
        while True:
            address = self._recv_from
            data, addr = self.recv_data.read_data()
            tcpheader = TCPHeader.from_bytes(data)
            result = result + tcpheader.PAYLOAD
        return data

    


    def send(self, tcpheader):
        address = self._send_to
        self.udp_socket.sendto(tcpheader, address)

        self.table[tcpheader.SEQ + len(tcpheader.PAYLOAD.encode())] = (tcpheader, 0)

        
        # threading.Thread(target=self.send_handler, daemon=True).start()
        # threading.Thread(target=self.timeout_handler, daemon=True).start()

    def sendall():
        # 这里需要完成整个重传的逻辑，比如哪些块要重传
        raise  NotImplementedError()


    def handler(self):
        # send 和 recv不能进行递归调用，统一在这里进行处理，因为send 和 recv本质是对等的，都是TCP协议。需要在handler中做的事情有

        # 1. 我们会维护一个tcpheader的Table，保存着未被确认的tcpheader。
        # 2. 确认收到的seqack 是可以确认我们的数据
        # 3. 查询chacksum，以确定数据是否损坏，损坏的话调用send函数进行重传
        # 4. 如果没有被confirm的TCP，直接重发。如果confirm的TCP，直接不管。（ACKSEQ == TCP.SEQ 情况下重发这个TCP， 如果ACKSEQ == TCP.SEQ + len() 这个TCP任务结束了）
        while True:
            data, addr = self.buffer.read_data(1024)
            tcpheader = TCPHeader.from_bytes(data)

            if self.checksum(tcpheader):
                if tcpheader.SEQACK in self.table:
                    del self.table[tcpheader.SEQACK]
                    self.recv_data.add_data(data, addr)
                else:
                    for i in self.table.keys():
                        #这里需要修改ACKSEQ为对方的SEQ+len(data)或者data为空的情况下，是SEQ+1
                        if self.table[i][0].SEQ == tcpheader.SEQACK:
                            old_tcpheader = self.table[i][0]
                            if len(tcpheader.PAYLOAD) == 0:
                                new_tcpheader = TCPHeader(SYN=old_tcpheader.SYN, FIN=old_tcpheader.FIN, ACK=old_tcpheader.ACK, SEQ=old_tcpheader.SEQ, SEQACK= tcpheader.SEQ + 1 , PAYLOAD=old_tcpheader.PAYLOAD)
                            else:
                                new_tcpheader = TCPHeader(SYN=old_tcpheader.SYN, FIN=old_tcpheader.FIN, ACK=old_tcpheader.ACK, SEQ=old_tcpheader.SEQ, SEQACK= tcpheader.SEQ + len(tcpheader.PAYLOAD.encode()) , PAYLOAD=old_tcpheader.PAYLOAD)
                            self.send(new_tcpheader)
                    else:
                        continue
            else:
                error_response = TCPHeader(SYN=0, FIN=0, ACK=1, SEQ=self.SEQ, SEQACK=tcpheader.SEQ)
                self.send(error_response)

    def checksum(self, tcpheader: TCPHeader):
        raise  NotImplementedError()

    def timeout_handler(self):
        while True:
            for i in self.table.keys():
                if self.table[i][1] >= self.TTL:
                    self.send(self.table[i][0])
                else:
                    self.table[i][1] = self.table[i][1] + 1
            time.sleep(1)

    def set_TTL(self, value):
        self.TTL = value
        
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
