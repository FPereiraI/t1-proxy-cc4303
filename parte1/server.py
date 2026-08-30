"""
Servidor HTTP mínimo de prueba.

Este script implementa un servidor TCP simple que acepta una única
conexión entrante, ignora el contenido del request recibido, y
responde siempre con una misma página HTML de prueba fija, incluyendo
el header personalizado X-ElQuePregunta.

Uso:
    python server.py <archivo_config.json>

El archivo de configuración JSON debe contener al menos el campo
"user", el cual se imprime en consola al iniciar el script.

El servidor escucha en 127.0.0.1:8000, atiende un único cliente, envía
la respuesta HTTP completa (header + body) y cierra tanto la conexión
del cliente como el socket servidor.
"""

import socket
import sys
import json

HOST = "127.0.0.1"

with open(sys.argv[1]) as file:
    data = json.load(file)
    user = data["user"]
    print(user)

body = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>TEST</title>
</head>
<body>
    <h1>Esto es una prueba</h1>
    <h3>Probando</h3>
</body>
"""
body_bytes = body.encode("utf-8")
content_length = len(body_bytes)

header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nX-ElQuePregunta: Fabián\r\nContent-Length: {content_length}\r\nConnection: close\r\n\r\n"

msg = header + body

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, 8000))
server_socket.listen(1)

new_socket, new_socket_address = server_socket.accept()
r_bytes = new_socket.recv(1024)

new_socket.send(msg.encode("utf-8"))

new_socket.close()
server_socket.close()