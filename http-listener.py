import http.server
import logging
import logging.handlers
import argparse
import os
import daemon
import signal

# Ustawienia folderu logów i pliku logowania
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'http_requests.log')

# Upewnij się, że folder logów istnieje
os.makedirs(LOG_DIR, exist_ok=True)

# Konfiguracja loggera z rotacją plików
log_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE, 
    when="midnight", 
    interval=1, 
    backupCount=0  # Brak ograniczenia liczby plików zapasowych
)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logging.getLogger().addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)

class MyRequestHandler(http.server.BaseHTTPRequestHandler):
    # Usuwamy informacje o wersji serwera
    server_version = "CustomHTTP/1.0"
    sys_version = ""

    def _log_request(self):
        """Logowanie nagłówków oraz wiadomości."""
        # Logowanie metody, ścieżki oraz adresu IP
        client_ip, _ = self.client_address
        logging.info(f"IP Klienta: {client_ip}, Metoda: {self.command}, Ścieżka: {self.path}")

        # Logowanie nagłówków
        headers = str(self.headers)
        logging.info(f"Nagłówki:\n{headers}")

        # Obsługa odczytu danych "chunked"
        if self.headers.get('Transfer-Encoding') == 'chunked':
            logging.info("Odczyt danych w trybie chunked.")
            post_data = self._read_chunked_data()
            logging.info(f"Wiadomość (chunked):\n{post_data}")
        else:
            # Odczyt wiadomości dla normalnych żądań
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                logging.info(f"Wiadomość:\n{post_data}")
            else:
                logging.info("Brak treści w wiadomości")

        # Dodanie separatora między żądaniami
        logging.info("\n" + "-"*40 + "\n")

    def _read_chunked_data(self):
        """Odczytuje dane w trybie chunked i zwraca całą wiadomość jako ciąg tekstowy."""
        data = []
        while True:
            # Każdy fragment ma nagłówek z rozmiarem fragmentu w szesnastkowym formacie
            chunk_size_str = self.rfile.readline().strip().decode('utf-8')
            try:
                chunk_size = int(chunk_size_str, 16)
            except ValueError:
                logging.error(f"Nieprawidłowy rozmiar chunk: {chunk_size_str}")
                return ''.join(data)

            if chunk_size == 0:
                # Koniec fragmentów
                break

            # Odczyt fragmentu danych o rozmiarze chunk_size
            chunk_data = self.rfile.read(chunk_size).decode('utf-8')
            data.append(chunk_data)

            # Odczyt nowej linii oddzielającej fragmenty
            self.rfile.read(2)  # \r\n

        return ''.join(data)

    def handle_one_request(self):
        """Obsługuje jedno żądanie HTTP."""
        try:
            # Metoda ta przetwarza nagłówki żądania i ustawia zmienne takie jak self.command, self.path itd.
            self.raw_requestline = self.rfile.readline()
            if not self.raw_requestline:
                return False

            if not self.parse_request():
                return False

            # Logowanie żądania
            self._log_request()

            # Odpowiadamy tylko statusem 200 bez dodatkowych informacji
            self.send_response(200)
            self.end_headers()
            return True
        except Exception as e:
            logging.error(f"Błąd podczas obsługi żądania: {e}")
            self.send_error(500, f"Internal Server Error: {e}")
            return False

def run_server(port):
    server_address = ('', port)  # Serwer nasłuchuje na porcie podanym przez użytkownika
    httpd = http.server.HTTPServer(server_address, MyRequestHandler)
    
    print(f"Serwer działa na porcie {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    # Dodanie argumentów z linii komend
    parser = argparse.ArgumentParser(description='Prosty serwer HTTP logujący wszystkie żądania, w tym dane chunked.')
    parser.add_argument('--port', type=int, default=8080, help='Numer portu, na którym serwer będzie nasłuchiwał (domyślnie 8080).')
    args = parser.parse_args()

    # Konfiguracja loggera musi być ustawiona przed wejściem do kontekstu demona
    logging.info("Rozpoczynanie serwera...")

    # Uruchom serwer jako demona
    with daemon.DaemonContext(
        signal_map={
            signal.SIGTERM: 'terminate',
        },
        stdout=open('/dev/null', 'w+'),
        stderr=open('/dev/null', 'w+'),
        files_preserve=[log_handler.stream],  # Zachowanie dostępu do pliku logowania
    ):
        run_server(args.port)
