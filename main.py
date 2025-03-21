from pathlib import Path
import mimetypes
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
DATA_FILE = STORAGE_DIR / "data.json"
jinja2 = Environment(loader=FileSystemLoader("storage"))


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html("templates/index.html")
            case "/message":
                self.send_html("templates/message.html")
            case "/read":
                self.send_read_page()
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("templates/error.html", status=404)

    def do_POST(self):
        if self.path == "/message":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            form_data = urllib.parse.parse_qs(post_data)

            username = form_data.get("username", [""])[0]
            message = form_data.get("message", [""])[0]

            if username and message:
                self.save_message(username, message)
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
            else:
                self.send_html("templates/error.html", status=400)

    def send_read_page(self):
        messages = self.load_messages()
        template = jinja2.get_template("read.html")
        html_content = template.render(messages=messages)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def load_messages(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_message(self, username, message):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        timestamp = datetime.now().isoformat()
        data[timestamp] = {"username": username, "message": message}

        with open(DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)


    def send_html(self, filename, status=200):
        file_path = BASE_DIR / filename.lstrip("/")
        if not file_path.exists():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(file_path, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status=200):
        self.send_response(status)
        mime_type,_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header("Content-type", mime_type)
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())



def run():
    server_address = ("", 3000)
    httpd = HTTPServer(server_address, MyHandler)
    print("Server started on port 3000")
    httpd.serve_forever()

if __name__ == "__main__":
    run()