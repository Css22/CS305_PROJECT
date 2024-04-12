import struct
import socket
import json
# 构建TCP 数据 header



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
        # 序列化
        # control_bits = (self.SYN << 2) | (self.FIN << 1) | self.ACK
        # header = struct.pack('!B3x4s4sLH', control_bits, self.SEQ, self.SEQACK, self.LEN, self.CHECKSUM)
        # if self.PAYLOAD:
        #     payload = self.PAYLOAD.encode() 
        #     return header + payload
        # else:
        #     return header
        json_data =  {
            "SYN": self.SYN,
            "FIN": self.FIN,
            "ACK": self.ACK,
            "SEQ": self.SEQ.hex() if self.SEQ else None,
            "SEQACK": self.SEQACK.hex() if self.SEQACK else None,
            "LEN": self.LEN,
            "CHECKSUM": self.CHECKSUM,
            "PAYLOAD": self.PAYLOAD if isinstance(self.PAYLOAD, str) else self.PAYLOAD.hex() if self.PAYLOAD else None
        }

        return json.dumps(json_data)
    
    def to_string(self, data):
        # 反序列化
        data = json.loads(data)
        self.SYN = data["SYN"]
        self.FIN = data['FIN']
        self.ACK = data['ACK']
        self.SEQ = bytes.fromhex(data["SEQ"]) if data["SEQ"] else None,
        self.SEQACK =bytes.fromhex(data["SEQACK"]) if data["SEQACK"] else None,
        self.LEN = data['LEN']
        self.CHECKSUM = data['CHECKSUM']
        self.PAYLOAD = data['PAYLOAD']

        return self


class TCPSocket():
    def __init__(self, rate=None) -> None:
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rate = rate
        self._send_to = None
        self._recv_from = None


    def listen(self, address):
        self.udp_socket.bind(address)
        while True:
            data, addr = self.udp_socket.recvfrom(1024)
          
            tcpheader = TCPHeader().to_string(data.decode())

            print(tcpheader.PAYLOAD)

    def accept(self,  address:(str, int)):
    
        raise NotImplementedError()
    


    def connect():
        raise NotImplementedError()

    


    def recv():
        raise NotImplementedError()
    


    def send():
        raise NotImplementedError()
    


    def close():
        pass




if __name__ == '__main__':
    port = 12345
    ip = "127.0.0.1"
    address = (ip, port)
    a = TCPSocket()

    a.listen(address)
