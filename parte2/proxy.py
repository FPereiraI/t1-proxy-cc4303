import socket
import sys
import json

# Para utilizar las funciones parser
sys.path.append("parte1")
sys.path.append("../parte1")
from parse_http import parse_HTTP_message, create_HTTP_message

HOST = "127.0.0.1"

# Para abrir JSON
if len(sys.argv) > 1:
    with open(sys.argv[1]) as file:
        data = json.load(file)
        print("JSON cargado")

# Parte server del proxy
proxy_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server_socket.bind((HOST, 8000))
proxy_server_socket.listen(1)
print(f"Proxy iniciado esperando en {HOST}:8000")

proxy_new_socket, client_address = proxy_server_socket.accept()
print(f"Cliente conectado desde {client_address[0]}:{client_address[1]}")

r_bytes = proxy_new_socket.recv(1024)
print(f"Request recibido")

(header, body) = parse_HTTP_message(r_bytes)
target_host = header.get("Host").strip()

# para no usar conexión keep alive
header.add("Connection", "close")

# parte cliente del proxy
proxy_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print(f"Conectando al servidor de destino {target_host}:80")
proxy_client_socket.connect((target_host, 80))
print(f"Conectado al servidor de destino {target_host}:80")

print("Reenviando request al servidor")
proxy_client_socket.send(create_HTTP_message((header, body)))

response_server = b""
while True:
    chunk = proxy_client_socket.recv(1024)
    if not chunk:
        break
    response_server += chunk

print("Respuesta del servidor recibida")

# envio del mensaje del server al cliente
print("Reenviando respuesta al cliente")
proxy_new_socket.send(response_server)

proxy_server_socket.close()
proxy_client_socket.close()
proxy_new_socket.close()
print("fin")
