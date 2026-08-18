import json
import socket
import sys

HOST = "127.0.0.1"

# toma un mensaje http, lo divide en header y body, pasa el header a un diccionario para facilitar su acceso y retorna el par (header, body)
def parse_HTTP_message(http_message: bytes):
    msg_header, msg_body = http_message.split(b"\r\n\r\n", 1) # divide el mensaje en headers y body separados por \r\n\r\n

    # bytes a string
    msg = msg_header.decode("utf-8")
    body = msg_body.decode("utf-8")

    lines  = msg.split("\r\n")

    header = {} # diccionario con los valores del header, e.g. fields["Host"] == "www.example.com"
    header["start-line"] = lines[0] # guarda la start line

    for line in lines[1:]: # guarda el resto del header en el diccionario header
        key, value = line.split(":", 1)
        header[key] = value

    return (header, body)