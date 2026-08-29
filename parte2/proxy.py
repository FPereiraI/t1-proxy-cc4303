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
        user = data["user"]
        blocked = []
        for domain in data["blocked"]:
            blocked.append(domain)
        forbidden_words = []
        for word in data["forbidden_words"]:
            forbidden_words.append(word)

# Parte server del proxy
proxy_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server_socket.bind((HOST, 8000))
proxy_server_socket.listen(2)
print(f"Proxy iniciado esperando en {HOST}:8000")

while True:
    proxy_new_socket, client_address = proxy_server_socket.accept()
    print(f"Cliente conectado desde {client_address[0]}:{client_address[1]}")

    r_bytes = proxy_new_socket.recv(1024)
    print(f"Request recibido")

    (header, body) = parse_HTTP_message(r_bytes)
    target_host = header.get("Host").strip()

    # se extrae el path de la start-line GET /miu.jpg HTTP/1.1
    start_line = header.get("start-line")
    method, path, version = start_line.split(" ")
    if method == "CONNECT":
        print(f"Metodo CONNECT no soportado, ignorando: {path}")
        proxy_new_socket.close()
        continue

    # segunda peticion del navegador para pedir la imagen miu
    if path.endswith("/miu.jpg"):
        with open("miu.jpg", "rb") as img_file:
            img_bytes = img_file.read()

        header_text = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(img_bytes)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        response = header_text.encode() + img_bytes
        proxy_new_socket.send(response)

    # dominio bloqueado
    elif any(b in (target_host + path) for b in blocked):
        print(f"Dominio bloqueado {target_host}{path}")
        html = (
            "<html><body>"
            "<h1>403 Forbidden</h1>"
            "<img src='/miu.jpg'>"
            "</body></html>"
        )
        html_bytes = html.encode()

        header_text = (
            "HTTP/1.1 403 Forbidden\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_bytes)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        response = header_text.encode() + html_bytes
        proxy_new_socket.send(response)

    # dominio no bloqueada
    else:
        # para no usar conexión keep alive
        header.add("Connection", "close")

        header.add("X-ElQuePregunta", "Fabián Pereira")

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

        (resp_header, resp_body) = parse_HTTP_message(response_server)

        # reemplazar palabras prohibidas
        for word_dict in forbidden_words:
            for word, replacement in word_dict.items():
                resp_body = resp_body.replace(word, replacement)

        new_length = len(resp_body.encode("utf-8"))

        # actualiza el content length
        for h in resp_header.headers:
            if h["name"].strip() == "Content-Length":
                h["value"] = " " + str(new_length)
                break

        # se vuelve a armar el mensaje completo con el body ya modificado
        response_server = create_HTTP_message((resp_header, resp_body))

        # envio del mensaje del server al cliente
        print("Reenviando respuesta al cliente")
        proxy_new_socket.send(response_server)

        proxy_client_socket.close()

    proxy_new_socket.close()
    print("fin de conexión")

proxy_server_socket.close()