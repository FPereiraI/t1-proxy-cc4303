import json
import socket
import sys


class Header:
    """
    Representa el conjunto de headers de un mensaje HTTP.

    Almacena los headers como una lista de diccionarios en vez de un
    diccionario simple, para soportar el caso en que un mismo nombre de
    header se repita con distintos valores (por ejemplo, Set-Cookie),
    lo cual no sería posible con una estructura de diccionario clásica
    sin perder información.

    Attributes:
        headers (list[dict]): Lista de diccionarios con la forma
            {"name": str, "value": str}, uno por cada línea del header
            original (incluyendo la start-line, guardada bajo el nombre
            "start-line").
    """

    def __init__(self):
        self.headers = []

    def add(self, name: str, value: str) -> None:
        """
        Agrega un nuevo header a la lista.

        Args:
            name (str): Nombre del header (por ejemplo "Host").
            value (str): Valor asociado al header.

        Returns:
            None
        """
        self.headers.append(
            {
                "name": name,
                "value": value
            }
        )

    def get(self, name: str) -> str | None:
        """
        Busca y retorna el valor del primer header cuyo nombre coincida
        con el entregado.

        No contempla el caso de headers repetidos con distintos valores;
        retorna únicamente la primera coincidencia encontrada.

        Args:
            name (str): Nombre del header a buscar.

        Returns:
            str | None: El valor asociado al header si existe,
                o None si no se encontró ningún header con ese nombre.
        """
        for h in self.headers:
            if h["name"] == name:
                return h["value"]
        return None


def parse_HTTP_message(http_message: bytes) -> tuple[Header, str]:
    """
    Parsea un mensaje HTTP completo (en bytes) y lo separa en header y body.

    Divide el mensaje en dos secciones usando el separador "\\r\\n\\r\\n",
    decodifica ambas secciones a texto, y procesa el header línea por
    línea para construir un objeto Header. La start-line (primera línea
    del mensaje, por ejemplo "GET / HTTP/1.1") se guarda dentro del
    objeto Header bajo el nombre "start-line". El body se retorna tal
    cual, sin procesar.

    Args:
        http_message (bytes): Mensaje HTTP completo, incluyendo header
            y body, tal como se recibe desde un socket.

    Returns:
        tuple[Header, str]: Tupla con el objeto Header construido a
            partir de las líneas del header, y el body como string.
    """
    msg_header, msg_body = http_message.split(b"\r\n\r\n", 1)

    msg = msg_header.decode()
    body = msg_body.decode()

    lines = msg.split("\r\n")

    header = Header()

    header.add("start-line", lines[0])

    for line in lines[1:]:
        key, value = line.split(":", 1)
        header.add(key, value)

    return (header, body)


def create_HTTP_message(parsed_msg: tuple[Header, str]) -> bytes:
    """
    Reconstruye un mensaje HTTP completo (en bytes) a partir de un
    objeto Header y un body.

    Es la operación inversa a parse_HTTP_message: toma la start-line y
    el resto de los headers almacenados en el objeto Header, los
    concatena con su formato original ("nombre:valor\\r\\n"), agrega la
    línea vacía separadora, y finalmente concatena el body.

    Args:
        parsed_msg (tuple[Header, str]): Tupla con el objeto Header y el
            body del mensaje a reconstruir.

    Returns:
        bytes: Mensaje HTTP completo, listo para ser enviado por un socket.
    """
    msg = ""

    header, body = parsed_msg
    msg += header.get("start-line") + "\r\n"

    for h in header.headers[1:]:
        msg += h["name"] + ":" + h["value"] + "\r\n"

    msg += "\r\n"
    msg += body

    return msg.encode()