from TCP import *
import socket

port = 12345
ip = "127.0.0.1"
address = (ip, port)
# a = TCPSocket()

# a.connect(address)


TCP_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket.bind(address)

TCP_socket.accept()
TCP_socket.recv()
# udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# udp_socket.accept()
# udp_socket.connect(address)


content = "test"
tcp_header = TCPHeader(SYN=1, FIN=0, ACK=0, SEQ=b'\x00\x00\x00\x01', SEQACK=b'\x00\x00\x00\x01', LEN=20, CHECKSUM=0xABCD, PAYLOAD=content)
udp_socket.send(tcp_header.to_bytes().encode())
