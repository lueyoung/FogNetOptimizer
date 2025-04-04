# IoT Simulation Environment

This repository provides a simulation environment for evaluating data transmission in Fog-Cloud IoT architectures. The simulation framework integrates an ns-3 module (written in C++) for IoT data generation, a fog node module (Python) for real-time entropy estimation, adaptive network coding, and scheduling decisions, and a cloud node module (Python) for performance monitoring and feedback control.

The system uses TCP sockets for inter-module communication with custom ports (6000 and 6001), avoiding the default port 5000.

------

## Table of Contents

- [Overview](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#overview)
- [Project Structure](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#project-structure)
- [Installation](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#installation)
- [Usage](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#usage)
- [Configuration](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#configuration)
- [Simulation Parameters](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#simulation-parameters)
- [Performance Metrics](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#performance-metrics)
- [Future Directions](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#future-directions)
- [License](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/67ef380c-8334-8013-a4f5-e3d8dcd35406#license)

------

## Overview

Traditional network coding strategies often fail to adapt to the dynamic nature of IoT data streams. Our framework addresses these issues by integrating:

- **Real-time entropy estimation:** Utilizing sliding window techniques and tensor-based predictive modeling.
- **Adaptive network coding:** Dynamically adjusts the coding degree ($dt$) and coding scheme ($C_t$) based on the estimated entropy.
- **Scheduling and feedback control:** A hybrid evolutionary-reinforcement learning (HE-RL) algorithm optimizes packet scheduling while considering constraints such as latency, bandwidth, and energy consumption.

The ultimate goal is to maximize bandwidth utilization, minimize transmission delay, and reduce energy consumption in Fog-Cloud IoT environments.

------

## Project Structure

```
iot-simulation/
├── iot_device/
│   └── src/
│       └── main.cc              # Main simulation code generating IoT data packets
├── fog_node/
│   ├── src/
│   │   ├── fog_node.py          # Implements fog node functionality (entropy estimation, coding, scheduling)
│   │   └── socket_comm.py       # Handles TCP communication with ns-3 and cloud node
│   └── requirements.txt         # Python dependencies (e.g., numpy, scipy)
├── cloud_node/
│   ├── src/
│   │   ├── cloud_node.py        # Implements cloud node functionality (performance evaluation, feedback control)
│   │   └── socket_comm.py       # Handles TCP communication with the fog node
│   └── requirements.txt         # Python dependencies
└── README.md                    # This file
```

For further details, refer to the project documentation files provided in the repository.

------

## Installation

### Prerequisites

- **C++ Development Environment:** Ensure you have a C++ compiler (e.g., GCC) and the necessary tools to compile ns-3.
- **Python 3:** Install Python 3.9 along with the required libraries listed in the `requirements.txt` files for both the fog node and cloud node modules.
- **ns-3:** Download and install ns-3.37 from the [ns-3 website](https://www.nsnam.org/).

### Build and Set Up

1. **Compile ns-3 Module:**

   - Navigate to the `iot_device/src/` directory.
   - Build the ns-3 simulation code.

2. **Install Python Dependencies:**

   - For the **fog_node** module, navigate to the `fog_node/` directory and run:

     ```bash
     python3 -m pip install -r requirements.txt
     ```

   - For the **cloud_node** module, navigate to the `cloud_node/` directory and run:

     ```bash
     python3 -m pip install -r requirements.txt
     ```

------

## Usage

### Running the Simulation

1. **Start the ns-3 Simulation:**

   - Execute the compiled ns-3 binary (e.g., built from `main.cc`). This module generates IoT data packets and sends them via TCP to the fog node on port **6000**.

2. **Run the Fog Node Module:**

   - From the `fog_node/src/` directory, run:

     ```bash
     python3 fog_node.py
     ```

   - The fog node listens on port **6000** for incoming data, processes the packets using a sliding window of 100 packets, performs entropy estimation, and applies adaptive network coding and scheduling decisions. It then sends the processed data to the cloud node on port **6001**.

3. **Run the Cloud Node Module:**

   - From the `cloud_node/src/` directory, run:

     ```bash
     python3 cloud_node.py
     ```

   - The cloud node listens on port **6001** for data from the fog node, performs performance evaluation, and sends feedback control signals back to the fog node.

### Stopping the Simulation

Terminate each module by pressing `Ctrl+C` in their respective terminal windows.

------

## Configuration

Key configuration details are defined within the source code:

- **TCP Communication Ports:**
  - **ns-3 Module:** Sends data to the fog node on port **6000**.
  - **Fog Node Module:** Listens on port **6000** and sends processed data to the cloud node on port **6001**.
  - **Cloud Node Module:** Listens on port **6001**.
- **Simulation Parameters:**
  - **Sliding Window Size ($W$):** $100$ packets.
  - **Data Alphabet Size ($n$):** $256$ symbols.
  - **Tensor Dimensionality ($d$):** $3$.
  - **Network Coding Degree ($dt$):** $2 \le dt \le 10$.
  - **Entropy Thresholds:** $H_{\text{low}} = 4.0$, $H_{\text{med}} = 6.0$ (used for selecting the appropriate coding scheme).
  - **Number of IoT Devices:** $1{,}000$.
  - **Packet Round ($\text{numPackets}$):** $100$ per IoT device.
  - **Other Constraints:**
    - **Latency Constraint ($L_{\text{max}}$):** $100\ \text{ms}$.
    - **Bandwidth Constraint ($B_{\text{total}}$):** $1\ \text{Gbps}$.
    - **Energy Constraint ($E_{\text{total}}$):** $100\ \text{J}$.
    - **Simulation Duration ($T$):** $10{,}000$ time steps.

You may modify these parameters directly in the source files to suit your specific needs.

------

## Simulation Parameters

The simulation settings, as described in Table II and throughout the manuscript, are as follows:

- **Sliding Window Size ($W$):** $100$ packets.
- **Data Alphabet Size ($n$):** $256$ symbols.
- **Tensor Dimensionality ($d$):** $3$.
- **Network Coding Degree ($dt$):** $2 \le dt \le 10$.
- **Coding Schemes ($C_t$):** ${\text{RLNC, Fountain, Simple}}$.
- **Entropy Thresholds:** $H_{\text{low}} = 4.0$, $H_{\text{med}} = 6.0$ (used for selecting the coding scheme).
- **Number of IoT Devices:** $1{,}000$.
- **Packet Round ($\text{numPackets}$):** $100$ per device.
- **Feedback Metrics Frequency:** Every $100$ time steps.
- **Other Constraints:**
  - **Latency Constraint ($L_{\text{max}}$):** $100\ \text{ms}$.
  - **Bandwidth Constraint ($B_{\text{total}}$):** $1\ \text{Gbps}$.
  - **Energy Constraint ($E_{\text{total}}$):** $100\ \text{J}$.
  - **Simulation Duration ($T$):** $10{,}000$ time steps.

These parameters ensure that the simulation reflects the conditions outlined in the literature.

------

## Performance Metrics

The simulation framework evaluates system performance using several key metrics:

1. **Bandwidth Utilization Efficiency ($\eta_{BW}$):**
    This metric measures the effective information transmitted per unit bandwidth. It is defined as:

   ηBW=∑t∑iSi(t)⋅Ii(t)∑t∑iSi(t)⋅B(Pi)\eta_{BW} = \frac{\sum_{t}\sum_{i} S_i(t) \cdot I_i(t)}{\sum_{t}\sum_{i} S_i(t) \cdot B(P_i)}

   where $S_i(t)$ indicates whether packet $i$ at time $t$ is transmitted, $I_i(t)$ is its mutual information, and $B(P_i)$ is its bandwidth consumption.

2. **Transmission Latency ($\Lambda$):**
    The average delay in transmitting packets is given by:

   Λ=1T⋅Nt∑t∑iSi(t)⋅Λ(Pi)\Lambda = \frac{1}{T \cdot N_t} \sum_{t}\sum_{i} S_i(t) \cdot \Lambda(P_i)

   where $\Lambda(P_i)$ is the transmission delay for packet $i$, $T$ is the total simulation time, and $N_t$ is the number of packets at time $t$.

3. **Total Energy Consumption ($E_{\text{total}}$):**
    This is the sum of energy consumed for transmitting packets:

   Etotal=∑t∑iSi(t)⋅E(Pi)E_{\text{total}} = \sum_{t}\sum_{i} S_i(t) \cdot E(P_i)

   where $E(P_i)$ is the energy required for packet $i$.

4. **Transmission Reliability ($R$):**
    Reliability is defined as the ratio of successfully transmitted packets:

   R=∑t∑iSi(t)⋅R(Pi)∑t∑iSi(t)R = \frac{\sum_{t}\sum_{i} S_i(t) \cdot R(P_i)}{\sum_{t}\sum_{i} S_i(t)}

   where $R(P_i)$ is $1$ for a successful transmission and $0$ otherwise.

5. **Throughput ($\Theta$):**
    Throughput measures the average mutual information transmitted per unit time:

   Θ=∑t∑iSi(t)⋅Ii(t)T\Theta = \frac{\sum_{t}\sum_{i} S_i(t) \cdot I_i(t)}{T}

For further details on these formulas and their implementation, please refer to the accompanying documentation.

------

## License

This project is licensed under the [MIT License](https://chatgpt.com/g/g-p-67ebe1bbbd80819194579f4971841598-iot-impl/c/LICENSE).