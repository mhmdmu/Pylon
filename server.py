import logging
import socket

log = logging.getLogger(__name__)


class TCPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def listen(self, handler):
        with socket.create_server((self.host, self.port)) as server:
            log.info(f"Server running on http://{self.host}:{self.port}")

            while True:
                conn, addr = server.accept()
                log.info(f"Client connected: {addr[0]}:{addr[1]}")

                raw_request = self._recv_full(conn)
                raw_response = handler(raw_request)
                
                conn.sendall(raw_response)
                conn.close()

    def _recv_full(self, conn: socket.socket) -> bytes:
        """Read the full HTTP request respecting Content-Length."""
        data = b""
        break_line = b"\r\n\r\n"

        # Read until we have the full header section
        while break_line not in data:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk

        header_part, _, body_so_far = data.partition(break_line)

        # Parse Content-Length from raw headers
        content_length = 0
        for line in header_part.split(b"\r\n")[1:]:
            if line.lower().startswith(b"content-length:"):
                try:
                    content_length = int(line.split(b":", 1)[1].strip())
                except ValueError:
                    pass
                break

        # Read remaining body bytes if needed
        while len(body_so_far) < content_length:
            chunk = conn.recv(1024)
            if not chunk:
                break
            body_so_far += chunk

        return header_part + break_line + body_so_far
