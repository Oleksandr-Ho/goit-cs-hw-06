from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import urllib.parse
import mimetypes
import pathlib
import datetime
import multiprocessing
import socketserver
from pymongo import MongoClient

class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Розбір запитаного URL
        pr_url = urllib.parse.urlparse(self.path)
        # Маршрутизація основних HTML сторінок
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            # Перевірка наявності статичних файлів і відправлення їх
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                # Повернення сторінки помилки при незнайденому файлі
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        # Відправлення HTML файлу
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        # Відправлення статичних файлів (CSS, images)
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        self.send_header("Content-type", mt[0] if mt[0] else 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

    def do_POST(self):
        # Обробка POST запитів (дані з форми)
        data = self.rfile.read(int(self.headers['Content-Length']))
        
        # Створення сокет-з'єднання для передачі даних
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 5000))
        client_socket.sendall(data)
        print('Дані успішно надіслано на сокет-сервер.')
        client_socket.close()
        
        # Перенаправлення користувача назад на сторінку з формою
        self.send_response(302)
        self.send_header('Location', '/message.html')
        self.end_headers()

def run_http():
    # Налаштування та запуск HTTP-сервера
    http = socketserver.TCPServer(('', 3000), HttpHandler)
    print('HTTP-сервер стартував і чекає на підключення...')
    http.serve_forever()     

def run_socket():
    # Налаштування та запуск сокет-сервера
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 5000))
    server_socket.listen(1)
    print('Socket-сервер стартував і чекає на підключення...')

    while True:
        client_socket, addr = server_socket.accept()
        print(f'Підключено від клієнта {addr}.')
        try:
            # Обробка даних, отриманих від клієнта
            data = client_socket.recv(1024).decode()
            data_parse = urllib.parse.unquote_plus(data)
            data_dict = {"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}
            data_dict.update({key: value for key, value in [el.split('=') for el in data_parse.split('&')]})
            print(f'Отримано дані: {data_dict}')
            work_with_mongo(data_dict)
        finally:
            client_socket.close()

def work_with_mongo(data_dict):
    # З'єднання з базою даних MongoDB та зберігання документа
    client = MongoClient("mongodb://mongodb:27017/")
    db = client['goit-cs-hw-06']
    collection = db['Messages']
    result = collection.insert_one(data_dict)
    print(f'Документ збережено з ID: {result.inserted_id}')

if __name__ == '__main__':
    # Запуск HTTP і сокет серверів у різних процесах
    http_process = multiprocessing.Process(target=run_http)
    http_process.start()

    socket_process = multiprocessing.Process(target=run_socket)
    socket_process.start()

    try:
        http_process.join()
        socket_process.join()
    except KeyboardInterrupt:
        http_process.terminate()
        socket_process.terminate()
        print("Сервери HTTP та Socket були зупинені.")
