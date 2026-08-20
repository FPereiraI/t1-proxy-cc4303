import json
import socket
import sys

# inicialmente lo hice con un diccionario simple pero después vi que en un header se puede repetir la misma clave con varios valores (Set-Cookie)
# con diccionario simple esa informacion se sobreeescribe y se pierde
# esto es una lista con diccionarios, un diccionario por linea del header, de la forma {"name": name, "value": value}
class Header:
    def __init__(self):
        self.headers = []

    def add(self, name, value):
        self.headers.append(
            {
                "name": name,
                "value": value
            }
        )

# no se considera el caso de nombre repetido con diferentes claves aún
    def get(self, name):
        for h in self.headers:
            if h["name"] == name:
                return h["value"]
        return None


# toma un mensaje http, lo divide en header y body, pasa el header a un diccionario para facilitar su acceso y retorna el par (header, body)
# extrae linea por linea el header, el body lo retorna intacto como string
def parse_HTTP_message(http_message: bytes):
    msg_header, msg_body = http_message.split(b"\r\n\r\n", 1) # divide el mensaje en headers y body separados por \r\n\r\n

    # bytes a string
    msg = msg_header.decode("utf-8")
    body = msg_body.decode("utf-8")

    lines  = msg.split("\r\n")

    header = Header() # objeto Header con los valores del header, e.g. header.get("Host") retorna "www.example.com"

    header.add("start-line", lines[0]) # guarda la start line

    for line in lines[1:]: # guarda el resto del header
        key, value = line.split(":", 1)
        header.add(key, value)

    return (header, body)

def create_HTTP_message(parsed_msg: tuple[Header, str]):
    msg = ""

    header, body = parsed_msg
    msg += header.get("start-line") + "\r\n"

    for h in header.headers[1:]:
        msg += h["name"] + ":" + h["value"] + "\r\n"

    msg += "\r\n" #agrega el "\r\n" extra q separa el header del body
    msg += body

    return msg.encode("utf-8")