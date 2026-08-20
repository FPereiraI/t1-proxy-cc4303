import socket
import sys
import json

HOST = "127.0.0.1"

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, 8000))
server_socket.listen(1)


new_socket, new_socket_address = server_socket.accept()
r_bytes = new_socket.recv(1024)

print(r_bytes)

new_socket.close()
server_socket.close()



