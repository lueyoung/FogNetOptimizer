#!/usr/bin/env python3
"""
Main processing flow of the cloud node:
1. Listen for data from the fog node via TCP (including encoded data and extended performance metrics 'info').
2. Parse the received data, separate the encoded data and the 'info' dictionary, and convert the info string into a dictionary using ast.literal_eval.
3. Store each received performance info in a global list and call compute_performance_metrics() to calculate system-level performance metrics.
4. Based on the aggregated results, execute a feedback control strategy to generate feedback information and return it to the fog node in JSON format.
5. At the same time, record the computed performance metrics (for example, write them to a log or save to a file) for subsequent data analysis and comparison of multiple schemes.
"""

import socket
import logging
import threading
import ast
import time
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [CloudNode] %(message)s',
    handlers=[logging.StreamHandler()]
)

# Global list for storing each received performance record (each record is an 'info' dictionary)
performance_records = []

def compute_performance_metrics():
    """
    Calculate the following performance metrics based on the accumulated performance_records:
      1. Bandwidth Utilization Efficiency (η_BW) = (∑ total_mutual_info) / (∑ total_bandwidth)
      2. Average Transmission Delay (Λ) = (∑ total_latency) / (∑ total_transmissions)
      3. Total Energy Consumption (E_total) = ∑ total_energy
      4. Transmission Reliability (R) = (∑ successful_transmissions) / (∑ total_transmissions)
      5. Throughput (Θ) = (∑ total_mutual_info) / (∑ time_steps)
    If any denominator is 0, the corresponding metric returns 0.
    Returns a dictionary containing these metrics.
    """
    global performance_records
    if not performance_records:
        return {}

    total_mutual_info = sum(rec.get("total_mutual_info", 0) for rec in performance_records)
    total_bandwidth = sum(rec.get("total_bandwidth", 0) for rec in performance_records)
    total_latency   = sum(rec.get("total_latency", 0) for rec in performance_records)
    total_energy    = sum(rec.get("total_energy", 0) for rec in performance_records)
    successful_tx   = sum(rec.get("successful_transmissions", 0) for rec in performance_records)
    total_tx        = sum(rec.get("total_transmissions", 0) for rec in performance_records)
    total_time      = sum(rec.get("time_steps", 0) for rec in performance_records)

    eta_bw = total_mutual_info / total_bandwidth if total_bandwidth > 0 else 0
    avg_latency = total_latency / total_tx if total_tx > 0 else 0
    reliability = successful_tx / total_tx if total_tx > 0 else 0
    throughput = total_mutual_info / total_time if total_time > 0 else 0

    metrics = {
        "bandwidth_utilization_efficiency": eta_bw,
        "average_latency": avg_latency,
        "total_energy": total_energy,
        "transmission_reliability": reliability,
        "throughput": throughput
    }
    return metrics

def record_metrics(metrics):
    """
    Record the computed performance metrics to the file 'performance_metrics.log',
    writing one JSON-formatted record per line.
    """
    filename = "performance_metrics.log"
    try:
        with open(filename, "a") as f:
            f.write(json.dumps(metrics) + "\n")
        logging.info(f"Recorded performance metrics to {filename}: {metrics}")
    except Exception as e:
        logging.error(f"Failed to write performance metrics log: {e}")

class CloudNode:
    def __init__(self, listen_ip="0.0.0.0", listen_port=6001):
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.lock = threading.Lock()

    def handle_connection(self, client_sock, addr):
        """
        Handle each TCP connection:
         - Receive data, parse the encoded data and the info string.
         - Record the performance info to the global list and call compute_performance_metrics() to calculate system-level metrics.
         - Generate feedback control information and return it to the fog node in JSON format.
        """
        try:
            data = client_sock.recv(65535)
            if not data:
                logging.warning(f"Received empty data from {addr}")
                client_sock.close()
                return
            
            logging.info(f"Received {len(data)} bytes of data from {addr}")
            # Data format: Encoded data and info string are separated by b"||"
            parts = data.split(b"||")
            if len(parts) < 2:
                logging.error("Data format error: missing separator '||'")
                client_sock.sendall(b"FormatError")
                client_sock.close()
                return
            
            encoded_data = parts[0]
            info_str = parts[1].decode()
            try:
                info = ast.literal_eval(info_str)
            except Exception as e:
                logging.error(f"Error parsing info dictionary: {e}")
                info = {}
            
            logging.info(f"Received performance info: {info}")
            # Record the info into the global performance records list
            with self.lock:
                performance_records.append(info)
            
            # Calculate the aggregated performance metrics
            metrics = compute_performance_metrics()
            logging.info(f"Aggregated performance metrics: {metrics}")
            # Write the performance metrics to the log file
            record_metrics(metrics)
            
            feedback = {}
            if metrics.get("bandwidth_utilization_efficiency", 0) < 0.5:
                feedback["adjust_dt"] = -1
                feedback["message"] = "Low bandwidth efficiency detected, consider reducing coding degree."
            else:
                feedback["adjust_dt"] = 1
                feedback["message"] = "Bandwidth efficiency is satisfactory, consider increasing coding degree."
            
            feedback["aggregated_metrics"] = metrics
            feedback_str = json.dumps(feedback)
            logging.info(f"Feedback control information: {feedback_str}")
            # Send feedback information back to the fog node
            client_sock.sendall(feedback_str.encode())
        except Exception as e:
            logging.error(f"Error handling connection: {e}")
        finally:
            client_sock.close()

    def start_server(self):
        """
        Start the TCP server, listen on the specified address and port, and handle each connection.
        """
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind((self.listen_ip, self.listen_port))
        server_sock.listen(5)
        logging.info(f"TCP server started, listening on {self.listen_ip}:{self.listen_port}")
        while True:
            try:
                client_sock, addr = server_sock.accept()
                logging.info(f"Accepted connection from {addr}")
                thread = threading.Thread(target=self.handle_connection, args=(client_sock, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                logging.error(f"TCP server error: {e}")

def main():
    try:
        cloud_node = CloudNode(listen_ip="0.0.0.0", listen_port=6001)
        logging.info("Starting cloud node...")
        cloud_node.start_server()
    except Exception as e:
        logging.error(f"Error in cloud node main function: {e}")

if __name__ == "__main__":
    main()
