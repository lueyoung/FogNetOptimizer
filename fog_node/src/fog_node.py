#!/usr/bin/env python3
"""
Implement the main processing flow of the fog node:
1. Receive IoT device data packets (via the socket_comm interface).
2. Use a sliding window to construct a tensor X_t ∈ R^(W x 256 x 3), where each packet's probability distribution (256-dimensional) is first calculated and then replicated three times to form three channels.
3. Perform Tucker decomposition (HOSVD) on the tensor and calculate the entropy within the window (using the probability distribution of each packet to calculate entropy, then taking the average).
4. Use an AR(3) model to predict the next moment's entropy value (falling back to AR(1) if historical data is insufficient).
5. Select network coding parameters based on the entropy value (current and predicted): coding scheme Ct and coding degree dt.
6. Perform network coding on the packets within the window (using XOR coding grouped by dt).
7. Calculate the priority of each packet (using the packet's entropy and energy consumption, applying gamma1 * entropy - gamma2 * energy, and introducing random perturbation).
8. Utilize a multi-dimensional 0-1 knapsack algorithm to select the packets to be scheduled under given bandwidth and energy constraints.
9. In addition to the above processing, calculate key performance indicators: total mutual information, total bandwidth, total delay, total energy consumption, transmission success rate, and window coverage time, etc.
   Send these pieces of information along with the encoded data to the cloud node via TCP.
"""

import threading
import time
import math
import numpy as np
import logging
import random
import traceback
import sys
import json

try:
    import tensorly as tl
    from tensorly.decomposition import tucker
    TENSORLY_AVAILABLE = True
except ImportError:
    TENSORLY_AVAILABLE = False
    logging.warning("Warning: tensorly library is not installed, Tucker decomposition functionality will be unavailable")

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s [%(levelname)s] [FogNode] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class FogNode:
    def __init__(self, cloud_host, cloud_port, window_size=100):
        self.cloud_host = cloud_host
        self.cloud_port = cloud_port
        self.window_size = window_size
        self.sliding_window = []
        self.lock = threading.Lock()
        self.entropy_history = []  
        self.ar_params = [0.5, 0.3, 0.2]  
        self.ar_const = 0.1             
        self.ar_a = 0.9  
        self.ar_b = 0.1
        self.H_low = 4.0
        self.H_med = 6.0
        self.coding_scheme = None
        self.coding_degree = None  
        self.gamma1 = 1.0
        self.gamma2 = 0.5
        self.bandwidth_capacity = 60
        self.energy_capacity = 60
        self.base_bandwidth = 1.0
        self.base_energy = 1.0
        
        logging.info(f"FogNode initialization complete, cloud node address: {cloud_host}:{cloud_port}, window size: {window_size}")


    def data_callback(self, data, addr):
        """
        Callback function: Called when a data packet is received, adds the data to the sliding window; if the window is full, starts processing
        """
        try:
            logging.info(f"Received data packet from {addr}, size: {len(data)} bytes")
            with self.lock:
                if not data or len(data) == 0:
                    logging.warning("Received data packet is empty, ignoring")
                    return
                logging.info(f"First 20 bytes of the data packet: {data[:20]}")
                self.sliding_window.append(data)
                logging.info(f"Current window size: {len(self.sliding_window)}/{self.window_size}")
                if len(self.sliding_window) >= self.window_size:
                    logging.info("Window is full, starting data processing...")
                    window_copy = self.sliding_window.copy()
                    self.sliding_window = []
                    processing_thread = threading.Thread(
                        target=self.process_sliding_window, 
                        args=(window_copy,)
                    )
                    processing_thread.daemon = False
                    processing_thread.start()
                    logging.info(f"Starting processing thread: {processing_thread.name}")
        except Exception as e:
            logging.error(f"Error occurred during data processing callback: {e}")
            logging.error(traceback.format_exc())

    def process_sliding_window(self, packets):
        """
        Process the data packets in the sliding window:
        1. Construct tensor representation: For each packet, calculate a 256-dimensional probability distribution and replicate it three times to form a (W, 256, 3) tensor.
        2. Perform HOSVD using Tucker decomposition.
        3. Calculate the window entropy (average entropy of each packet).
        4. Use an AR(3) model to predict the next moment's entropy value (falling back to AR(1) if historical data is insufficient).
        5. Select network coding parameters (Ct and dt) based on the entropy value.
        6. Perform XOR encoding on the window packets grouped by the coding degree dt to simulate network coding.
        7. Calculate the priority for each packet and use a multi-dimensional 0-1 knapsack algorithm for scheduling decisions.
        8. Calculate performance metrics: total mutual information, total bandwidth, total delay, total energy consumption, transmission success rate, and window duration.
        9. Encapsulate the encoding results, scheduling information, and performance metrics and send them via TCP to the cloud node.
        """
        try:
            logging.info(f"Starting to process window data: {len(packets)} packets")
            W = len(packets)
            # 1. Construct tensor: Convert each packet to a 256-dimensional probability distribution, replicate three times to form (W, 256, 3)
            tensor = np.zeros((W, 256, 3))
            packet_entropies = []
            for i, packet in enumerate(packets):
                try:
                    data_array = np.frombuffer(packet, dtype=np.uint8)
                    logging.debug(f"Packet {i}: Data array size {len(data_array)}")
                    hist, _ = np.histogram(data_array, bins=256, range=(0, 256), density=True)
                    tensor[i, :, :] = np.tile(hist.reshape(256, 1), (1, 3))
                    nonzero = hist[hist > 0]
                    ent = -np.sum(nonzero * np.log2(nonzero))
                    packet_entropies.append(ent)
                    logging.debug(f"Packet {i}: Entropy value = {ent:.3f} bits")
                except Exception as e:
                    logging.error(f"Error occurred while processing packet {i}: {e}")
                    logging.error(traceback.format_exc())
                    packet_entropies.append(5.0)
            
            # 2. Tucker decomposition (HOSVD)
            try:
                if TENSORLY_AVAILABLE:
                    logging.info("Executing Tucker decomposition...")
                    core, factors = tucker(tensor, rank=[min(W, 10), min(256, 10), 3])
                    logging.info(f"Tucker decomposition completed, core tensor shape: {core.shape}")
                else:
                    logging.warning("Tucker decomposition is unavailable, skipping this step")
                    core = tensor
            except Exception as e:
                logging.error(f"Tucker decomposition failed: {e}")
                logging.error(traceback.format_exc())
                core = tensor
    
            # 3. Calculate current window entropy: Take the average of all packet entropies
            current_entropy = np.mean(packet_entropies)
            logging.info(f"Current window entropy: {current_entropy:.3f} bits")
            # Save current entropy to history list for AR(3) prediction
            self.entropy_history.append(current_entropy)
            
            # 4. Use AR(3) model to predict the next moment's entropy value, falling back to AR(1) if historical data is insufficient
            if len(self.entropy_history) >= 3:
                predicted_entropy = (
                    self.ar_params[0] * self.entropy_history[-1] +
                    self.ar_params[1] * self.entropy_history[-2] +
                    self.ar_params[2] * self.entropy_history[-3] +
                    self.ar_const
                )
                logging.info("Using AR(3) model to predict the next moment's entropy value")
            else:
                predicted_entropy = self.ar_a * current_entropy + self.ar_b
                logging.info("Insufficient historical data, using AR(1) model to predict the next moment's entropy value")
            logging.info(f"Predicting entropy: {predicted_entropy:.3f} bits")
    
            # 5. Select network coding parameters based on entropy value
            self.decide_coding_parameters(current_entropy)
            logging.info(f"Selected coding scheme: {self.coding_scheme}, coding degree dt = {self.coding_degree}")
    
            # 6. Network coding: Group packets by coding degree dt and perform XOR encoding on the packets
            encoded_packet = self.perform_network_coding(packets, self.coding_degree)
            logging.info(f"Encoded packet length: {len(encoded_packet)} bytes")
    
            # 7. Scheduling decision: Calculate the priority for each packet and use a multi-dimensional 0-1 knapsack algorithm to select packets for transmission 
            items = []
            for i, p in enumerate(packets):
                ent = packet_entropies[i]
                bw = self.base_bandwidth * (1 + random.uniform(-0.1, 0.1))
                energy = self.base_energy * (1 + random.uniform(-0.1, 0.1))
                value = self.gamma1 * ent - self.gamma2 * energy
                items.append((value, int(bw * 10), int(energy * 10)))
            capacity_bw = self.bandwidth_capacity * 10
            capacity_energy = self.energy_capacity * 10
            selected_indices = self.multi_dim_knapsack(items, capacity_bw, capacity_energy)
            scheduled_packets = [packets[i] for i in selected_indices]
            logging.info(f"Scheduled {len(scheduled_packets)} packets through the multi-dimensional knapsack algorithm")
    
            # 8. Calculate performance metrics
            total_mutual_info = sum(packet_entropies)
            total_bandwidth = sum(len(p) * (1 + random.uniform(-0.1, 0.1)) for p in packets)
            latencies = [random.uniform(0.01, 0.1) for _ in range(len(packets))]
            total_latency = sum(latencies)
            energies = [len(p) * 0.001 * (1 + random.uniform(-0.1, 0.1)) for p in packets]
            total_energy = sum(energies)
            successful_transmissions = len(packets)
            total_transmissions = len(packets)
            time_steps = len(packets) * 0.5
    
            performance_info = {
                "total_mutual_info": total_mutual_info,
                "total_bandwidth": total_bandwidth,
                "total_latency": total_latency,
                "total_energy": total_energy,
                "successful_transmissions": successful_transmissions,
                "total_transmissions": total_transmissions,
                "time_steps": time_steps
            }
    
            # 9. Assemble send information: Merge the original info with performance metrics and send
            info = {
                "current_entropy": current_entropy,
                "predicted_entropy": predicted_entropy,
                "coding_scheme": self.coding_scheme,
                "coding_degree": self.coding_degree,
                "num_scheduled": len(scheduled_packets)
            }
            info.update(performance_info)
            info_str = json.dumps(info)
            send_data = encoded_packet + b"||" + info_str.encode()
            
            from socket_comm import send_tcp_message
            logging.info(f"Attempting to send processing results to the cloud node: {self.cloud_host}:{self.cloud_port}")
            response = send_tcp_message(self.cloud_host, self.cloud_port, send_data)
            if response:
                logging.info(f"Cloud node response: {response}")
            else:
                logging.warning("No response received from the cloud node")
        
        except Exception as e:
            logging.error(f"Error occurred during processing of the sliding window: {e}")
            logging.error(traceback.format_exc())
    
    def decide_coding_parameters(self, entropy):
        """
        Select coding scheme and coding degree based on the current entropy value:
          - If entropy < H_low, select "Simple", dt = 2
          - If H_low ≤ entropy < H_med, select "Fountain", dt = 4
          - If entropy ≥ H_med, select "RLNC", dt = 6
        """
        if entropy < self.H_low:
            self.coding_scheme = "Simple"
            self.coding_degree = 2
        elif entropy < self.H_med:
            self.coding_scheme = "Fountain"
            self.coding_degree = 4
        else:
            self.coding_scheme = "RLNC"
            self.coding_degree = 6

    def perform_network_coding(self, packets, dt):
        """
        Perform XOR encoding on the packets within the window grouped by the coding degree dt.
        If the last group has fewer than dt packets, perform XOR encoding on the remaining data as well.
        Return the concatenated byte string of all group encoding results.
        """
        if not packets:
            return b""
        encoded_groups = []
        num_groups = math.ceil(len(packets) / dt)
        logging.info(f"Executing network coding: {len(packets)} packets divided into {num_groups} groups")
        
        for i in range(num_groups):
            group = packets[i * dt : (i + 1) * dt]
            arrays = [np.frombuffer(p, dtype=np.uint8) for p in group]
            max_length = max(len(arr) for arr in arrays)
            padded_arrays = []
            for arr in arrays:
                if len(arr) < max_length:
                    padded = np.zeros(max_length, dtype=np.uint8)
                    padded[:len(arr)] = arr
                    padded_arrays.append(padded)
                else:
                    padded_arrays.append(arr)
            encoded = padded_arrays[0].copy()
            for arr in padded_arrays[1:]:
                encoded = np.bitwise_xor(encoded, arr)
            encoded_groups.append(encoded.tobytes())
            logging.debug(f"Group {i}: Encoded {len(group)} packets, result length {len(encoded.tobytes())} bytes")
        
        result = b"".join(encoded_groups)
        logging.info(f"All groups encoding completed, total length {len(result)} bytes")
        return result

    def multi_dim_knapsack(self, items, capacity1, capacity2):
        """
        Solve the two-dimensional 0-1 knapsack problem, where items is a list where each element (value, weight1, weight2) is an integer.
        capacity1 and capacity2 are the two constraint capacities.
        Return a list of indices of the selected items, implemented using dynamic programming.
        """
        n = len(items)
        logging.debug(f"Starting to solve the multi-dimensional knapsack problem: {n} items, capacities: ({capacity1}, {capacity2})")
        DP = [[[0 for _ in range(capacity2 + 1)] for _ in range(capacity1 + 1)] for _ in range(n + 1)]
        keep = [[[False for _ in range(capacity2 + 1)] for _ in range(capacity1 + 1)] for _ in range(n + 1)]
        for i in range(1, n + 1):
            value, w, e = items[i - 1]
            for c1 in range(capacity1 + 1):
                for c2 in range(capacity2 + 1):
                    if w <= c1 and e <= c2:
                        if DP[i - 1][c1 - w][c2 - e] + value > DP[i - 1][c1][c2]:
                            DP[i][c1][c2] = DP[i - 1][c1 - w][c2 - e] + value
                            keep[i][c1][c2] = True
                        else:
                            DP[i][c1][c2] = DP[i - 1][c1][c2]
                    else:
                        DP[i][c1][c2] = DP[i - 1][c1][c2]
        selected = []
        c1 = capacity1
        c2 = capacity2
        for i in range(n, 0, -1):
            if keep[i][c1][c2]:
                selected.append(i - 1)
                _, w, e = items[i - 1]
                c1 -= w
                c2 -= e
        selected.reverse()
        logging.info(f"Multi-dimensional knapsack problem solved, selected {len(selected)} items")
        return selected

def main():
    try:
        listen_ip = "0.0.0.0"
        listen_port = 6000
        cloud_host = "cloud_node"  # Cloud node address
        cloud_port = 6001          # Cloud node listening port
    
        fog_node = FogNode(cloud_host, cloud_port, window_size=100)
    
        logging.info("Importing socket_comm module...")
        try:
            from socket_comm import start_tcp_server
            logging.info("Successfully imported socket_comm module")
        except ImportError as e:
            logging.error(f"Failed to import socket_comm module: {e}")
            logging.error(traceback.format_exc())
            return
        
        logging.info(f"Starting TCP server, listening {listen_ip}:{listen_port}...")
        server_thread = threading.Thread(
            target=start_tcp_server, 
            args=(listen_ip, listen_port, fog_node.data_callback)
        )
        server_thread.daemon = False
        server_thread.start()
        logging.info(f"TCP server thread has been started: {server_thread.name}")
    
        logging.info("Fog node running, waiting for incoming data...")
        server_thread.join()
    
    except Exception as e:
        logging.error(f"Error occurred during the execution of the main function: {e}")
        logging.error(traceback.format_exc())
    
    logging.info("Fog node shutdown.")

if __name__ == "__main__":
    main()

