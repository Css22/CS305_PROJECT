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
            "SEQACK": self.SEQACK.to_bytes(4, 'big').hex(),
            "LEN": self.LEN,
            "CHECKSUM": self.CHECKSUM,
            "PAYLOAD": self.PAYLOAD if isinstance(self.PAYLOAD, str) else self.PAYLOAD.hex() if self.PAYLOAD else None
        }

        return json.dumps(json_data).encode()
    
    def from_bytes(self, data):
        # if isinstance(data, bytes):
        #     data = data.decode()
        data = json.loads(data)
        self.SYN = data["SYN"]
        self.FIN = data['FIN']
        self.ACK = data['ACK']
        self.SEQ = int.from_bytes(bytes.fromhex(data["SEQ"]), 'big') if data["SEQ"] else None
        self.SEQACK = int.from_bytes(bytes.fromhex(data["SEQACK"]), 'big') if data["SEQACK"] else None
        self.LEN = data['LEN']
        self.CHECKSUM = data['CHECKSUM']
        self.PAYLOAD = data['PAYLOAD']

        return self

    def __str__(self) -> str:
        """
        Overwrite the toString function of this class
        """
        return f'SYN: {self.SYN}, FIN: {self.FIN}, ACK: {self.ACK}, SEQ: {self.SEQ}, SEQACK: {self.SEQACK}, LEN: {self.LEN}, CHECKSUM: {self.CHECKSUM}, PAYLOAD: {self.PAYLOAD}'



class ByteBuffer():
    def __init__(self, max_size = 212992, max_read = 1024):
        self.max_size = max_size
        self.max_read = max_read
        self.queue = queue.Queue()
        self.current_size = 0 
        self.cond = threading.Condition() 
    
    def add_data(self, data):
        with self.cond:
            # if not isinstance(data, bytes):
            #     raise ValueError("Data must be of type bytes.")
            allowable_size = 0
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
            data_read = ()
            while length > 0:
                while self.queue.empty():
                    self.cond.wait()

                data_chunk = self.queue.get()
                if len(data_chunk) <= length:
                    data_read += data_chunk
                    length -= len(data_chunk[0])
                    self.current_size -= len(data_chunk[0])
                    if self.queue.empty():
                        break
                else:
                    data_read += data_chunk[:length]
                    self.queue.put(data_chunk[0][length:])
                    self.current_size -= length
                    break
        return data_read





class TCPSocket():
    def __init__(self, TTL =3 ):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ACKSEQ =  None
        self.SEQ =  None
        self.address = None
        self.connections = {}
        self.buffer = ByteBuffer()
        self.TTL = TTL
        # table is the sliding window
        self.table = {}
        self.recv_data = ByteBuffer()
        self.chunk_size = None
        

    
    def buffer_handler(self):
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
            if addr not in self.connections.keys():
                print("add new data")
                self.buffer.add_data((data, addr))
            else:
                print("update data")
                self.connections[addr]['buffer'].add_data((data, addr))



    def bind(self, address):
        self.udp_socket.bind(address)
        self.address = address
        # threading.Thread(target=self.buffer_handler, daemon=True).start()


    def accept(self):
        """
        Establish connection with a comming TCP request.
        """
        # Start buffer handler to listen data
        threading.Thread(target=self.buffer_handler, daemon=True).start()

        # Keep checking
        while True:
            data, addr = self.buffer.read_data(1024)
            header = TCPHeader().from_bytes(data)
            if header.SYN == 1 and header.ACK == 0:
                # Receive 1st handshake from client.
                buffer = ByteBuffer()
                socket = TCPSocket()

                socket.SEQ = random.randint(0, 0xFFFFFFFF)
                SEQACK = header.SEQ + 1
                response = TCPHeader(SYN=1, ACK=1, SEQ=socket.SEQ ,SEQACK=SEQACK, PAYLOAD=None)
            
                socket.udp_socket = self.udp_socket
                socket.buffer = buffer
                socket.address = addr
                threading.Thread(target=socket.handler, daemon=True).start()

                self.connections[addr] = {'buffer': buffer, "socket": socket}
                # Send response to client and start the 2nd handshake
                socket.send(tcpheader=response)
                socket.SEQ = socket.SEQ + 1
                tcpheader, addr = socket.recv()
                if not tcpheader.PAYLOAD:
                    socket.ACKSEQ = tcpheader.SEQ + 1
                else:
                    socket.ACKSEQ = tcpheader.SEQ + len(tcpheader.PAYLOAD.encode())
                return socket


    def connect(self,  address:(str, int)): # type: ignore
        """
        Connet from client to server.
        params:
            address:    ip address and port of the destination server.
        """
        threading.Thread(target=self.buffer_handler, daemon=True).start()
        threading.Thread(target=self.handler, daemon=True).start()
        # 1st handshake
        self.SEQ = random.randint(0, 0xFFFFFFFF)
        header = TCPHeader(SYN=1, ACK=0, SEQ=self.SEQ, SEQACK=0)
        self.address = address
        self.send(tcpheader=header)
        self.SEQ = self.SEQ + 1
        # 2nd handshake
        tcpheader, addr =  self.recv()
        # if not tcpheader.PAYLOAD:
        #     self.ACKSEQ = tcpheader.SEQ + 1
        # else:
        #     self.ACKSEQ = tcpheader.SEQ + len(tcpheader.PAYLOAD.encode())

        if tcpheader.SYN == 1 and tcpheader.ACK == 1:  # This is a SYN-ACK packet
            ack_header = TCPHeader(ACK=1, SEQ=self.SEQ, SEQACK=tcpheader.SEQ + 1)
            self.send(tcpheader=ack_header)
            self.SEQ = self.SEQ+1
            

    def recv(self):
        data, addr = self.recv_data.read_data()
        tcpheader = TCPHeader().from_bytes(data)
        return tcpheader, addr

    


    def send(self, tcpheader: TCPHeader, data=None):
        if data:
            address = self.address
            tcpheader = TCPHeader(SYN=0, FIN=0, ACK=1, SEQ=self.SEQ, SEQACK=self.ACKSEQ,PAYLOAD=data)
            self.SEQ = self.SEQ + len(data.encode())
            self.udp_socket.sendto(tcpheader.to_bytes(), address)
            self.table[tcpheader.SEQ + len(tcpheader.PAYLOAD.encode())] = (tcpheader, self.TTL)
        else:
            address = self.address
            self.udp_socket.sendto(tcpheader.to_bytes(), address)
            if tcpheader.PAYLOAD:
                self.table[tcpheader.SEQ + len(tcpheader.PAYLOAD.encode())] = (tcpheader, self.TTL)
            else:
                self.table[tcpheader.SEQ + 1] = (tcpheader, self.TTL)
            print("testing!")

    def sendall(self) :
        # 这里需要完成将整个大文件分块传输的过程，以及在乱序的情况下，将包重新排序，以及pipline和sliding窗口的实现，还有拥塞控制

        #Base版本，滑动窗口为1的串行文件
        #调用send函数，发送数据

        #1. 大文件分块, 给定项目文档的pdf，将其转为bytes，
        chunk_size = 512

        #2. 循环传输，并写入到本地文件中,串行阻塞式

        for i in chunk_size:
            self.send()
            self.recv()
 


        raise  NotImplementedError()


    def handler(self):
        # send 和 recv不能进行递归调用，统一在这里进行处理，因为send 和 recv本质是对等的，都是TCP协议。需要在handler中做的事情有

        # 1. 我们会维护一个tcpheader的Table，保存着未被确认的tcpheader。
        # 2. 确认收到的seqack 是可以确认我们的数据
        # 3. 查询chacksum，以确定数据是否损坏，损坏的话调用send函数进行重传
        # 4. 如果没有被confirm的TCP，直接重发。如果confirm的TCP，直接不管。（ACKSEQ == TCP.SEQ 情况下重发这个TCP， 如果ACKSEQ == TCP.SEQ + len() 这个TCP任务结束了）
        while True:
            
            data, addr = self.buffer.read_data(1024)
            tcpheader = TCPHeader().from_bytes(data)
            
            if self.checksum(tcpheader):
        
                if tcpheader.ACK == 0:
                    self.recv_data.add_data((data, addr))

                if tcpheader.SEQACK in self.table.keys():
                    del self.table[tcpheader.SEQACK]
                    self.recv_data.add_data((data, addr))

                # 在现有机制下，如何主要接受对面要求重传的指令？
                # else:
                #     for i in self.table.keys():
                #         if self.table[i][0].SEQ == tcpheader.SEQACK:
                #             old_tcpheader = self.table[i][0]
                #             if tcpheader.PAYLOAD:
                #                 new_tcpheader = TCPHeader(SYN=old_tcpheader.SYN, FIN=old_tcpheader.FIN, ACK=old_tcpheader.ACK, SEQ=old_tcpheader.SEQ, SEQACK= tcpheader.SEQ + 1 , PAYLOAD=old_tcpheader.PAYLOAD)
                #             else:
                #                 new_tcpheader = TCPHeader(SYN=old_tcpheader.SYN, FIN=old_tcpheader.FIN, ACK=old_tcpheader.ACK, SEQ=old_tcpheader.SEQ, SEQACK= tcpheader.SEQ + len(tcpheader.PAYLOAD.encode()) , PAYLOAD=old_tcpheader.PAYLOAD)
                #             self.send(tcpheader=new_tcpheader)
            else:
                error_response = TCPHeader(SYN=0, FIN=0, ACK=1, SEQ=self.SEQ, SEQACK=tcpheader.SEQ)
                self.send(tcpheader=error_response)

    # def checksum(self, tcpheader: TCPHeader) -> bool:
    #     return True
    #     raise  NotImplementedError()

    def checksum(self, tcpheader: TCPHeader) -> bool:
        """
        Compare checksum of both local and received tcp request. If checksum correct, return true, otherwise return false.

        TODO: This function is still need to be verified its correctness.
        """
        return True
        recv_checksum = tcpheader.CHECKSUM
        data = tcpheader.SYN + tcpheader.FIN + tcpheader.ACK + tcpheader.SEQ + tcpheader.SEQACK + tcpheader.LEN + 0 + tcpheader.PAYLOAD
        checksum = 0
        # If the lenght of data is odd number, add an 0 to the end of data to make it become an even number
        if len(data) % 2 != 0:
            data += '0'
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i + 1]
            checksum += word
            # If overflow
            checksum = (checksum & 0xFFFF) + (checksum >> 16)

        # 1's complement
        checksum = ~checksum & 0xFFFF

        if checksum == recv_checksum:
            return True
        else:
            return False


    def timeout_handler(self):
        """
        This function is for checking the table and control the timeout.
        """
        while True:
            for i in self.table.keys():
                if self.table[i][1] < 0:
                    self.send(self.table[i][0])
                else:
                    self.table[i][1] = self.table[i][1] - 1
            time.sleep(1)

    def set_TTL(self, value):
        self.TTL = value

    def close(self):
        """
        Close current TCP connection.

        In TCP 4-way close progress.
        1st handshake: SEQ, ACK, FIN=1, ACK=1 which means the client want to close the connection
        2nd handshake: SEQ, ACK, FIN=None, ACK=1 which means the server received the FIN code from the client
        3rd handshake: SEQ, ACK, FIN=1, ACK=1 which means the client really want to close the connection
        4nd handshake: SEQ, ACK, FIN=Noe, ACK=1 which means the server confirm to close the connection.

        After this 4-way-handshake, the TCP connection will be terminated. 

        TODO: I don't confirm that how do you implement the exact accept and connet function.
        So I just list how does the 4-way-handshake work.
        头大，玛德，睡觉。
        """

        # Close the connection. And re-create new udp-socket. Or just re-bind  to another address??
        self.udp_socket.close()
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        raise  NotImplementedError()




if __name__ == '__main__':
    port = 12345
    ip = "127.0.0.1"
    
    selfport = 12334
    b_address = (ip, port)
    a = TCPSocket()
    a.bind((ip, selfport))
    a.connect(b_address)
    while True:
        tcpheader, addr = a.recv()
    
