#!/usr/bin/env python3

import socket
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [SocketComm] %(message)s')

def start_tcp_server(listen_ip, listen_port, callback):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((listen_ip, listen_port))
    server_sock.listen(5)
    logging.info(f"TCP server listening on {listen_ip}:{listen_port}")
    while True:
        try:
            client_sock, addr = server_sock.accept()
            data = client_sock.recv(65535)
            logging.info(f"TCP received {len(data)} bytes of data from {addr}")
            callback(data, addr)
            client_sock.sendall(b"ACK")
            client_sock.close()
        except Exception as e:
            logging.error(f"TCP server error: {e}")

def send_tcp_message(remote_host, remote_port, data):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((remote_host, remote_port))
        sock.sendall(data)
        response = sock.recv(4096)
        return response.decode()
    except Exception as e:
        logging.error(f"Error occurred while sending TCP message: {e}")
        return None
    finally:
        sock.close()

