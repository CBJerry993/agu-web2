"""Publish ETF matrix data to Redis.

Set REDIS_URL in the iQuant process environment, for example:
redis://:password@host:6379/0
"""
import os
import socket
import ssl
from urllib.parse import unquote, urlparse


REDIS_KEY = os.environ.get("ETF_MATRIX_REDIS_KEY", "agu:etf_matrix:latest")


def _encode_command(*parts: str) -> bytes:
    chunks = [f"*{len(parts)}\r\n".encode("utf-8")]
    for part in parts:
        payload = str(part).encode("utf-8")
        chunks.append(f"${len(payload)}\r\n".encode("utf-8"))
        chunks.append(payload + b"\r\n")
    return b"".join(chunks)


def _read_response(sock: socket.socket) -> bytes:
    data = sock.recv(4096)
    if not data:
        raise RuntimeError("Empty Redis response")
    if data.startswith(b"-"):
        raise RuntimeError(data.decode("utf-8", errors="replace"))
    return data


def publish_etf_matrix(data_json: str, key: str = REDIS_KEY) -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set")

    parsed = urlparse(redis_url)
    host = parsed.hostname
    port = parsed.port or (6380 if parsed.scheme == "rediss" else 6379)
    password = unquote(parsed.password or "")
    username = unquote(parsed.username or "")
    db = (parsed.path or "").lstrip("/")

    raw_sock = socket.create_connection((host, port), timeout=5)
    sock = ssl.create_default_context().wrap_socket(raw_sock, server_hostname=host) if parsed.scheme == "rediss" else raw_sock
    try:
        if password:
            if username:
                sock.sendall(_encode_command("AUTH", username, password))
            else:
                sock.sendall(_encode_command("AUTH", password))
            _read_response(sock)
        if db:
            sock.sendall(_encode_command("SELECT", db))
            _read_response(sock)
        sock.sendall(_encode_command("SET", key, data_json))
        _read_response(sock)
    finally:
        sock.close()
