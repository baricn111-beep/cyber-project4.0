import socket
import os
import mimetypes
import zipfile
from urllib.parse import unquote, parse_qs
import logging

# ================= CONFIGURATION =================
WEB_ROOT = r"C:\Users\Bari\OneDrive\Desktop\bari\4.0.py\webroot.zip"
DEFAULT_URL = "/index.html"
IP = '0.0.0.0'
PORT = 8080
SOCKET_TIMEOUT = 2
QUEUE_SIZE = 10

REDIRECTION_DICTIONARY = {"/moved/": "/index.html"}

# ================= LOGGING CONFIG =================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    filename='server.log',   # כל הלוגים יישמרו כאן
    filemode='a'             # 'a' = להוסיף בסוף הקובץ
)

# ================= FUNCTIONS =================

def get_file_data(file_name):
    """
    Retrieve file data from a ZIP archive
    """
    internal_path = file_name.lstrip("/")
    try:
        with zipfile.ZipFile(WEB_ROOT, 'r') as z:
            with z.open(internal_path) as f:
                return f.read()
    except Exception as e:
        logging.error(f"Error reading {file_name}: {e}")
        return None


def handle_client_request(resource, client_socket):
    """
    Generate HTTP response based on the requested resource and send it to the client
    """
    if "?" in resource:
        path, query_string = resource.split("?", 1)
    else:
        path, query_string = resource, ""

    if path == '/' or path == '':
        uri = DEFAULT_URL
    else:
        uri = path

    if uri in REDIRECTION_DICTIONARY:
        location = REDIRECTION_DICTIONARY[uri]
        header = f"HTTP/1.1 302 Found\r\nLocation: {location}\r\n\r\n"
        client_socket.send(header.encode())
        logging.info(f"Redirected {uri} to {location}")
        return

    if uri == '/forbidden/':
        header = "HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n"
        client_socket.send(header.encode())
        logging.info(f"Access forbidden for {uri}")
        return

    if "calculate-area" in uri:
        params = parse_qs(query_string)
        width = params.get('width', ['0'])[0]
        height = params.get('height', ['0'])[0]

        if width.isdigit() and height.isdigit():
            area = int(width) * int(height)
            result = f"The area is: {area}".encode()
            header = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(result)}\r\n\r\n"
            client_socket.send(header.encode() + result)
            logging.info(f"Calculated area: {area}")
        else:
            msg = b"Invalid parameters"
            header = f"HTTP/1.1 400 Bad Request\r\nContent-Length: {len(msg)}\r\n\r\n"
            client_socket.send(header.encode() + msg)
            logging.warning(f"Invalid parameters for calculate-area: width={width}, height={height}")
        return

    data = get_file_data(uri)
    if data is None:
        header = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
        client_socket.send(header.encode())
        logging.warning(f"File not found: {uri}")
        return

    content_type, _ = mimetypes.guess_type(uri)
    if content_type is None:
        content_type = 'application/octet-stream'

    http_header = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(data)}\r\n\r\n"
    client_socket.send(http_header.encode() + data)
    logging.info(f"Served file: {uri} (Content-Type: {content_type})")


def validate_http_request(request):
    """
    Validate if the incoming request is a proper HTTP GET request
    """
    if not request:
        return False, ""

    lines = request.splitlines()
    if len(lines) == 0:
        return False, ""

    parts = lines[0].split()
    if len(parts) != 3:
        return False, ""

    method, resource, version = parts
    if method != "GET" or not version.startswith("HTTP/"):
        return False, ""

    return True, resource


def handle_client(client_socket):
    """
    Handle incoming client connections and process their requests
    """
    logging.info('Client connected')
    try:
        client_request = client_socket.recv(1024).decode(errors='ignore')
        if not client_request:
            return

        valid_http, resource = validate_http_request(client_request)
        if valid_http:
            logging.info(f'Got a valid HTTP request for: {resource}')
            handle_client_request(resource, client_socket)
        else:
            logging.warning('Received invalid HTTP request')
            header = "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n"
            client_socket.send(header.encode())

    except socket.timeout:
        logging.warning('Timeout occurred')
    except Exception as e:
        logging.error(f'Error: {e}')
    finally:
        client_socket.close()
        logging.info('Closed connection')


def main():
    """
    Start the HTTP server and listen for client connections
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((IP, PORT))
        server_socket.listen(QUEUE_SIZE)
        logging.info(f"Listening for connections on {IP}:{PORT}")

        while True:
            client_socket, client_address = server_socket.accept()
            try:
                client_socket.settimeout(SOCKET_TIMEOUT)
                handle_client(client_socket)
            except socket.error as err:
                logging.error('Socket exception: ' + str(err))
    except socket.error as err:
        logging.error('Socket exception: ' + str(err))
    finally:
        server_socket.close()
        logging.info("Server shutdown")


if __name__ == "__main__":
    main()
