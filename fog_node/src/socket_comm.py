#!/usr/bin/env python3

import socket
import logging
import sys
import threading
import traceback

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s [%(levelname)s] [SocketComm] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def handle_client(client_socket, addr, callback):
    try:
        logging.info(f"Starting to process client connection from {addr}")
        client_socket.settimeout(10)
        
        buffer = bytearray()
        while True:
            try:
                chunk = client_socket.recv(4096)
                if not chunk:
                    logging.info(f"Client {addr} has closed the connection")
                    break
                
                buffer.extend(chunk)
                logging.debug(f"Received {len(chunk)} bytes of data from {addr}, current buffer size: {len(buffer)} bytes")
                
                if len(buffer) > 0:
                    # Call callback to process data
                    callback(bytes(buffer), addr)
                    # Send acknowledgment response
                    response = b"Received data successfully"
                    client_socket.sendall(response)
                    logging.info(f"Send acknowledgment response to {addr}: {response}")
                    buffer.clear()
            except socket.timeout:
                logging.warning(f"Client {addr} receive timeout")
                if len(buffer) > 0:
                    callback(bytes(buffer), addr)
                    buffer.clear()
                break
            except Exception as e:
                logging.error(f"Error occurred while receiving data: {e}")
                logging.error(traceback.format_exc())
                break
    except Exception as e:
        logging.error(f"Error occurred while processing client {addr}: {e}")
        logging.error(traceback.format_exc())
    finally:
        try:
            client_socket.close()
            logging.info(f"Connection with {addr} has been closed")
        except:
            pass

def start_tcp_server(listen_ip, listen_port, callback):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        logging.info(f"Attempting to bind TCP server on {listen_ip}:{listen_port}")
        sock.bind((listen_ip, listen_port))
        
        sock.listen(10)
        logging.info(f"TCP server successfully listening on {listen_ip}:{listen_port}")
        
        while True:
            try:
                client, addr = sock.accept()
                logging.info(f"Accepting connection from {addr}")
                
                client_thread = threading.Thread(
                    target=handle_client, 
                    args=(client, addr, callback)
                )
                client_thread.daemon = True
                client_thread.start()
                logging.debug(f"Started new thread for {addr}: {client_thread.name}")
            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, shutting down server...")
                break
            except Exception as e:
                logging.error(f"Error occurred while accepting connection: {e}")
                logging.error(traceback.format_exc())
                continue
    except Exception as e:
        logging.error(f"Failed to start TCP server: {e}")
        logging.error(traceback.format_exc())
        if sock:
            sock.close()
        return
    finally:
        if sock:
            try:
                sock.close()
                logging.info("TCP server socket has been closed")
            except:
                pass

def send_tcp_message(remote_host, remote_port, data):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        logging.info(f"Attempting to connect to {remote_host}:{remote_port}")
        sock.connect((remote_host, remote_port))
        
        sock.sendall(data)
        logging.info(f"Sent {len(data)} bytes to {remote_host}:{remote_port}")
        
        # 等待响应
        response = sock.recv(4096)
        logging.info(f"Received response from {remote_host}:{remote_port}: {len(response)} bytes")
        return response
    except Exception as e:
        logging.error(f"Error occurred while sending TCP message: {e}")
        logging.error(traceback.format_exc())
        return None
    finally:
        if sock:
            try:
                sock.close()
                logging.info(f"Connection with {remote_host}:{remote_port} has been closed")
            except:
                pass

# When this script is run directly, start a simple echo server for testing
if __name__ == "__main__":
    def echo_callback(data, addr):
        logging.info(f"Received {len(data)} bytes of data from {addr}")
        logging.debug(f"First 20 bytes of data: {data[:20]}")
    
    logging.info("Starting test TCP echo server...")
    start_tcp_server("0.0.0.0", 6000, echo_callback)
