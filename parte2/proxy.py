"""
Proxy HTTP con soporte de bloqueo de dominios, filtrado de contenido
y reensamblado de mensajes fragmentados.

Este script implementa un proxy HTTP que escucha conexiones entrantes,
reenvía las peticiones al servidor de destino indicado en el header
Host, y aplica las siguientes reglas antes de reenviar o responder:

- Si el dominio (u dominio + path) solicitado está en la lista de
  dominios bloqueados definida en el archivo de configuración JSON,
  responde con un código 403 y una página HTML que referencia una
  imagen local.
- Si la petición corresponde específicamente a esa imagen local
  (miu.jpg), la sirve directamente desde disco con código 200.
- Si el dominio no está bloqueado, reenvía la petición al servidor de
  destino, agregando el header personalizado X-ElQuePregunta, y antes
  de responder al cliente reemplaza en el body de la respuesta las
  palabras prohibidas definidas en el archivo de configuración,
  actualizando el header Content-Length según corresponda.
- Las peticiones con método CONNECT son ignoradas, ya que el proxy no
  soporta túneles HTTPS.

La recepción de mensajes (tanto request como response) se realiza
mediante funciones que acumulan datos en múltiples llamadas a recv(),
permitiendo que el proxy funcione correctamente incluso si el tamaño
del buffer de recepción configurado (RECV_BUFFER) es menor al tamaño
del mensaje HTTP a recibir.

Uso:
    python proxy.py <archivo_config.json>

El archivo de configuración JSON debe contener los campos "user",
"blocked" (lista de dominios o dominio+path bloqueados) y
"forbidden_words" (lista de diccionarios con la forma
{"palabra": "reemplazo"}).

Nota: el script debe ejecutarse estando ubicado dentro del directorio
parte2/, ya que la imagen miu.jpg se abre usando una ruta relativa al
directorio de trabajo actual. Ejecutarlo desde otro directorio (por
ejemplo, la raíz del proyecto) provoca un error al intentar cargar la
imagen. Se optó por esta solución más simple en vez de resolver la
ruta de forma independiente del directorio de ejecución.

El proxy escucha en 127.0.0.1:8000 y atiende conexiones de forma
secuencial en un ciclo indefinido.
"""

import socket
import sys
import json

# Para utilizar las funciones parser
sys.path.append("parte1")
sys.path.append("../parte1")
from parse_http import parse_HTTP_message, create_HTTP_message

HOST = "127.0.0.1"
RECV_BUFFER = 50

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


def recv_headers(scket: socket.socket, buffer_size: int) -> bytes:
    """
    Recibe datos desde un socket, acumulándolos hasta encontrar el
    separador que marca el final de los headers HTTP.

    Realiza llamadas sucesivas a recv() sobre el socket entregado,
    concatenando cada fragmento recibido, hasta que la secuencia
    "\\r\\n\\r\\n" (separador estándar entre headers y body en HTTP)
    aparezca dentro de los datos acumulados, o hasta que el socket no
    entregue más datos (conexión cerrada por el otro extremo).

    Args:
        scket (socket.socket): Socket desde el cual se reciben los datos.
        buffer_size (int): Tamaño máximo de bytes a leer en cada
            llamada a recv().

    Returns:
        bytes: Datos acumulados hasta encontrar el separador de
            headers (inclusive), o los datos parciales recibidos si la
            conexión se cerró antes de completar los headers.
    """
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = scket.recv(buffer_size)
        if not chunk:
            break
        data += chunk
    return data


def recv_message(scket: socket.socket, buffer_size: int) -> bytes:
    """
    Recibe un mensaje HTTP completo (headers y body) desde un socket,
    sin asumir que el buffer de recepción es suficientemente grande
    para recibirlo en una sola llamada.

    Primero utiliza recv_headers() para obtener los headers completos.
    Luego busca el header Content-Length dentro de ellos para
    determinar la cantidad de bytes que debe tener el body, y continúa
    llamando a recv() hasta acumular esa cantidad de bytes o hasta que
    el socket deje de entregar datos.

    Args:
        scket (socket.socket): Socket desde el cual se recibe el mensaje.
        buffer_size (int): Tamaño máximo de bytes a leer en cada
            llamada a recv().

    Returns:
        bytes: Mensaje HTTP completo (headers + separador + body). Si
            los headers no llegaron a completarse, retorna los datos
            parciales recibidos hasta el corte de la conexión.
    """
    data = recv_headers(scket, buffer_size)
    if b"\r\n\r\n" not in data:
        return data
    header_part, _, body_part = data.partition(b"\r\n\r\n")

    content_length = 0

    for line in header_part.split(b"\r\n"):
        if line.lower().startswith(b"content-length"):
            content_length = int(line.split(b":", 1)[1].strip())
            break

    body = body_part
    while len(body) < content_length:
        chunk = scket.recv(buffer_size)
        if not chunk:
            break
        body += chunk

    return header_part + b"\r\n\r\n" + body


# Parte server del proxy
proxy_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy_server_socket.bind((HOST, 8000))
proxy_server_socket.listen(2)
print(f"Proxy iniciado esperando en {HOST}:8000")

while True:
    proxy_new_socket, client_address = proxy_server_socket.accept()
    print(f"Cliente conectado desde {client_address[0]}:{client_address[1]}")

    r_bytes = recv_message(proxy_new_socket, RECV_BUFFER)
    print(f"Request recibido")

    (header, body) = parse_HTTP_message(r_bytes)
    target_host = header.get("Host").strip()

    # Se extrae el path de la start-line, ej: "GET /miu.jpg HTTP/1.1"
    start_line = header.get("start-line")
    method, path, version = start_line.split(" ")
    if method == "CONNECT":
        print(f"Metodo CONNECT no soportado, ignorando: {path}")
        proxy_new_socket.close()
        continue

    # Segunda petición del navegador: solicitud de la imagen local de bloqueo
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

    # Dominio (o dominio + path) bloqueado según el archivo de configuración
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

    # Dominio no bloqueado: comportamiento normal de reenvío
    else:
        # Para no usar conexión keep alive
        header.add("Connection", "close")

        header.add("X-ElQuePregunta", "Fabián Pereira")

        # Parte cliente del proxy
        proxy_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Conectando al servidor de destino {target_host}:80")
        proxy_client_socket.connect((target_host, 80))
        print(f"Conectado al servidor de destino {target_host}:80")

        print("Reenviando request al servidor")
        proxy_client_socket.send(create_HTTP_message((header, body)))

        response_server = recv_message(proxy_client_socket, RECV_BUFFER)
        print("Respuesta del servidor recibida")

        (resp_header, resp_body) = parse_HTTP_message(response_server)

        # Reemplazo de palabras prohibidas en el body de la respuesta
        for word_dict in forbidden_words:
            for word, replacement in word_dict.items():
                resp_body = resp_body.replace(word, replacement)

        new_length = len(resp_body.encode("utf-8"))

        # Actualización del Content-Length tras el reemplazo de palabras
        for h in resp_header.headers:
            if h["name"].strip() == "Content-Length":
                h["value"] = " " + str(new_length)
                break

        # Se vuelve a armar el mensaje completo con el body ya modificado
        response_server = create_HTTP_message((resp_header, resp_body))

        # Envío del mensaje del servidor al cliente
        print("Reenviando respuesta al cliente")
        proxy_new_socket.send(response_server)

        proxy_client_socket.close()

    proxy_new_socket.close()
    print("fin de conexión")

proxy_server_socket.close()