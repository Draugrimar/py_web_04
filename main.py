import urllib.parse
import mimetypes
import json
import logging
from threading import Thread
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = "0.0.0.0"
SOCKET_PORT = 5000
SOCKET_HOST = "localhost"


class GTFramework(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html("index.html")
            case "/messages":
                self.send_html("message.html")
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html(filename="error.html", status_code=404)

    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header(keyword="Location", value="/messages")
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header(keyword="Content-type", value="text/html")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header(keyword="Content-type", value=mime_type)
        else:
            self.send_header(keyword="Content-type", value="text/plain")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())


def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, GTFramework)
    logging.info("Starting http server")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()


def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            save_data_from_form(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()


def save_data_from_form(data):
    data_parse = urllib.parse.unquote_plus(data.decode())
    try:
        time = str(datetime.now())
        data_dict = {
            key: value for key, value in [el.split("=") for el in data_parse.split("&")]
        }

        with open("storage/data.json", "r+", encoding="utf=8") as file:
            json_dict = json.load(file)
            json_dict[time] = data_dict
            file.seek(0)
            file.truncate()
            json.dump(json_dict, file, ensure_ascii=False, indent=4)

    except ValueError as error:
        logging.error(error)
    except OSError as error:
        logging.error(error)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(threadName)s %(message)s")
    http_server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    http_server.start()

    socket_server = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    socket_server.start()
