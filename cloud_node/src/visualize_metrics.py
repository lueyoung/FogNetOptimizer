#!/usr/bin/env python3
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def load_performance_data(filename="performance_metrics.log"):
    """
    Load performance metrics data from the log file, where each line is a JSON-formatted record.
    Returns a pandas DataFrame.
    """
    data = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        data.append(record)
                    except Exception as e:
                        print(f"Failed to parse a line of data: {e}")
        if not data:
            print("No data was read. Please check the file contents.")
            return None
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def plot_bandwidth_utilization(df):
    plt.figure(figsize=(10, 6))
    plt.plot(df.index, df['bandwidth_utilization_efficiency'], marker='o', linestyle='-')
    plt.title('Bandwidth Utilization Efficiency')
    plt.xlabel('Time Step')
    plt.ylabel('Efficiency')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("bandwidth_utilization_efficiency_line.png")
    plt.show()

def plot_average_latency_violin(df):
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=df, y='average_latency')
    plt.title('Average Latency Violin Plot')
    plt.ylabel('Average Latency (s)')
    plt.tight_layout()
    plt.savefig("average_latency_violin.png")
    plt.show()

def plot_total_energy(df):
    plt.figure(figsize=(10, 6))
    plt.plot(df.index, df['total_energy'], marker='o', linestyle='-', color='orange')
    plt.title('Total Energy')
    plt.xlabel('Time Step')
    plt.ylabel('Total Energy (J)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("total_energy_line.png")
    plt.show()

def plot_transmission_reliability(df):
    plt.figure(figsize=(10, 6))
    sns.barplot(x=df.index, y='transmission_reliability', data=df, color='green')
    plt.title('Transmission Reliability')
    plt.xlabel('Time Step')
    plt.ylabel('Reliability')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("transmission_reliability_bar.png")
    plt.show()

def plot_throughput(df):
    plt.figure(figsize=(10, 6))
    plt.plot(df.index, df['throughput'], marker='o', linestyle='-', color='red')
    plt.title('Throughput')
    plt.xlabel('Time Step')
    plt.ylabel('Throughput (unit)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("throughput_line.png")
    plt.show()

def main():
    df = load_performance_data("performance_metrics.log")
    if df is None or df.empty:
        print("No valid data found, exiting.")
        return

    print(df.head())

    # Plot charts for each metric separately
    plot_bandwidth_utilization(df)
    plot_average_latency_violin(df)
    plot_total_energy(df)
    plot_transmission_reliability(df)
    plot_throughput(df)

if __name__ == "__main__":
    main()
