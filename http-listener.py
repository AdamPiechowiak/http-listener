import http.server
import logging
import logging.handlers
import argparse
import os

# Ustawienia folderu logów i pliku logowania
LOG_DIR = 'logs'
LOG_FILE = os.path.join(LOG_DIR, 'http_requests.log')

# Upewnij się, że folder logów istnieje
os.makedirs(LOG_DIR, exist_ok=True)

# Konfiguracja loggera
class MyRequestHandler(http.server.BaseHTTPRequestHandler):
    # Usuwamy informacje o wersji serwera
    server_version = "CustomHTTP/1.0"
    sys_version = ""

    def _log_request(self):
        """Logowanie naglowkow oraz wiadomosci."""
        # Logowanie metody, sciezki oraz adresu IP
        client_ip, _ = self.client_address
        logging.info(f"IP Klienta: {client_ip}, Metoda: {self.command}, Sciezka: {self.path}")

        # Logowanie naglowkow
        headers = str(self.headers)
        logging.info(f"Naglowki:\n{headers}")

        # Obsluga odczytu danych "chunked"
        if self.headers.get('Transfer-Encoding') == 'chunked':
            logging.info("Odczyt danych w trybie chunked.")
            post_data = self._read_chunked_data()
            logging.info(f"Wiadomosc (chunked):\n{post_data}")
        else:
            # Odczyt wiadomosci dla normalnych zadani
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                logging.info(f"Wiadomosc:\n{post_data}")
            else:
                logging.info("Brak tresci w wiadomosci")

        # Dodanie pustej linii jako separatora
        logging.info("\n" + "-"*40 + "\n")

    def _read_chunked_data(self):
        """Odczytuje dane w trybie chunked i zwraca cala wiadomosc jako ciag tekstowy."""
        data = []
        while True:
            # Kazdy fragment ma naglowek z rozmiarem fragmentu w szesnastkowym formacie
            chunk_size_str = self.rfile.readline().strip().decode('utf-8')
            try:
                chunk_size = int(chunk_size_str, 16)
            except ValueError:
                logging.error(f"Nieprawidlowy rozmiar chunk: {chunk_size_str}")
                return ''.join(data)

            if chunk_size == 0:
                # Koniec fragmentow
                break

            # Odczyt fragmentu danych o rozmiarze chunk_size
            chunk_data = self.rfile.read(chunk_size).decode('utf-8')
            data.append(chunk_data)

            # Odczyt nowej linii oddzielajacej fragmenty
            self.rfile.read(2)  # \r\n

        return ''.join(data)

    def handle_one_request(self):
        """Obsluguje jedno zadanie HTTP."""
        try:
            # Metoda ta przetwarza naglowki zadania i ustawia zmienne takie jak self.command, self.path itd.
            self.raw_requestline = self.rfile.readline()
            if not self.raw_requestline:
                return False

            if not self.parse_request():
                return False

            # Logowanie zadania
            self._log_request()

            # Odpowiadamy tylko statusem 200 bez dodatkowych informacji
            self.send_response(200)
            self.end_headers()
            return True
        except Exception as e:
            logging.error(f"Blad podczas obslugi zadania: {e}")
            self.send_error(500, f"Internal Server Error: {e}")
            return False

if __name__ == "__main__":
    # Dodanie argumentow z linii komend
    parser = argparse.ArgumentParser(description='Prosty serwer HTTP logujacy wszystkie zadania, w tym dane chunked.')
    parser.add_argument('--port', type=int, default=8080, help='Numer portu, na ktorym serwer bedzie nasluchiwal (domyslnie 8080).')
    args = parser.parse_args()

    # Konfiguracja loggera z rotacja plikow
    log_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILE, 
        when="midnight", 
        interval=1, 
        backupCount=0  # Brak ograniczenia liczby plikow zapasowych
    )
    log_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.INFO)

    server_address = ('', args.port)  # Serwer nasluchuje na porcie podanym przez uzytkownika
    httpd = http.server.HTTPServer(server_address, MyRequestHandler)
    
    print(f"Serwer dziala na porcie {args.port}...")
    httpd.serve_forever()
