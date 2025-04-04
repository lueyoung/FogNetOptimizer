#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/tcp-socket-factory.h"
#include "ns3/ipv4-address.h"
#include <random>
#include <string>
#include <netdb.h>
#include <arpa/inet.h>
#include <cstring>
#include <sys/types.h>
#include <sys/socket.h>
#include <unistd.h>
#include <sstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("IoTDataSimulation");

Ipv4Address ResolveHostname(const std::string &hostname) {
  struct addrinfo hints, *res;
  std::memset(&hints, 0, sizeof(hints));
  hints.ai_family = AF_INET;
  int err = getaddrinfo(hostname.c_str(), nullptr, &hints, &res);
  if (err != 0 || res == nullptr) {
    NS_LOG_ERROR("Failed to resolve hostname: " << hostname);
    return Ipv4Address("0.0.0.0");
  }
  char ip[INET_ADDRSTRLEN];
  struct sockaddr_in *addr = (struct sockaddr_in *)res->ai_addr;
  inet_ntop(AF_INET, &(addr->sin_addr), ip, INET_ADDRSTRLEN);
  Ipv4Address result(ip);
  freeaddrinfo(res);
  return result;
}

class TcpComm {
public:
  TcpComm() : m_sockfd(-1) {}
  ~TcpComm() { if(m_sockfd != -1) close(m_sockfd); }
  
  bool Connect(const std::string &host, uint16_t port) {
    struct addrinfo hints, *res, *p;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    
    std::stringstream port_ss;
    port_ss << port;
    std::string port_str = port_ss.str();
    
    int status = getaddrinfo(host.c_str(), port_str.c_str(), &hints, &res);
    if (status != 0) {
      NS_LOG_ERROR("getaddrinfo error: " << gai_strerror(status));
      return false;
    }
    
    for (p = res; p != NULL; p = p->ai_next) {
      m_sockfd = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
      if (m_sockfd == -1)
        continue;
        
      // set overtime
      struct timeval tv;
      tv.tv_sec = 5;
      tv.tv_usec = 0;
      setsockopt(m_sockfd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof tv);
      setsockopt(m_sockfd, SOL_SOCKET, SO_SNDTIMEO, (const char*)&tv, sizeof tv);
      
      if (connect(m_sockfd, p->ai_addr, p->ai_addrlen) == -1) {
        NS_LOG_ERROR("Connect error: " << strerror(errno));
        close(m_sockfd);
        m_sockfd = -1;
        continue;
      }
      break;
    }
    
    freeaddrinfo(res);
    if (p == NULL) {
      NS_LOG_ERROR("Failed to connect to " << host << ":" << port);
      return false;
    }
    
    NS_LOG_INFO("Successfully connected to " << host << ":" << port);
    return true;
  }
  
  ssize_t Send(const uint8_t* data, size_t length) {
    ssize_t bytes_sent = send(m_sockfd, data, length, 0);
    if (bytes_sent == -1) {
      NS_LOG_ERROR("Send error: " << strerror(errno));
    } else {
      NS_LOG_INFO("Sent " << bytes_sent << " bytes");
    }
    return bytes_sent;
  }
  
  void Disconnect() {
    if (m_sockfd != -1) {
      close(m_sockfd);
      m_sockfd = -1;
      NS_LOG_INFO("Connection closed");
    }
  }
  
private:
  int m_sockfd;
};

class IoTDataApp : public Application {
public:
  IoTDataApp();
  virtual ~IoTDataApp();
  void Setup(const std::string &fogHost, uint16_t fogPort, uint32_t packetSize, uint32_t numPackets, Time interval);

protected:
  virtual void StartApplication(void);
  virtual void StopApplication(void);

private:
  void SendPacket(void);
  double SimulateEntropy(void); // dynamic entropy value 

  std::string m_fogHost;
  uint16_t    m_fogPort;
  uint32_t    m_packetSize;
  uint32_t    m_numPackets;
  Time        m_interval;
  uint32_t    m_packetsSent;
  EventId     m_sendEvent;
  bool        m_running;
};

IoTDataApp::IoTDataApp()
  : m_fogHost(""),
    m_fogPort(0),
    m_packetSize(0),
    m_numPackets(0),
    m_interval(Seconds(0)),
    m_packetsSent(0),
    m_running(false)
{
}

IoTDataApp::~IoTDataApp() {
}

void IoTDataApp::Setup(const std::string &fogHost, uint16_t fogPort, uint32_t packetSize, uint32_t numPackets, Time interval) {
  m_fogHost = fogHost;
  m_fogPort = fogPort;
  m_packetSize = packetSize;
  m_numPackets = numPackets;
  m_interval = interval;
}

double IoTDataApp::SimulateEntropy(void) {
  static std::random_device rd;
  static std::mt19937 gen(rd());
  std::uniform_real_distribution<> dis(0.0, 1.0);
  return dis(gen);
}

void IoTDataApp::StartApplication(void) {
  m_running = true;
  m_packetsSent = 0;
  SendPacket();
}

void IoTDataApp::StopApplication(void) {
  m_running = false;
  if (m_sendEvent.IsRunning()) {
    Simulator::Cancel(m_sendEvent);
  }
}

void IoTDataApp::SendPacket(void) {
  if (!m_running) {
    return;
  }
  
  if (m_packetsSent < m_numPackets) {
    double entropy = SimulateEntropy();
    NS_LOG_INFO("Node " << GetNode()->GetId() 
                << " attempting to send packet " << (m_packetsSent + 1)
                << " with simulated entropy: " << entropy);
    
    uint8_t *packet_data = new uint8_t[m_packetSize];
    for (uint32_t i = 0; i < m_packetSize; i++) {
      packet_data[i] = rand() % 256;
    }
    
    TcpComm comm;
    if (comm.Connect(m_fogHost, m_fogPort)) {
      ssize_t sent = comm.Send(packet_data, m_packetSize);
      if (sent > 0) {
        m_packetsSent++;
        NS_LOG_INFO("Node " << GetNode()->GetId() 
                  << " successfully sent packet " << m_packetsSent);
      }
      comm.Disconnect();
    } else {
      NS_LOG_ERROR("Node " << GetNode()->GetId() 
                  << " failed to connect to " << m_fogHost << ":" << m_fogPort);
    }
    
    delete[] packet_data;
    
    // schedule the next sending
    m_sendEvent = Simulator::Schedule(m_interval, &IoTDataApp::SendPacket, this);
  }
}

int main(int argc, char *argv[]) {
  CommandLine cmd;
  std::string fogHost = "fog_node"; // fog node
  uint16_t fogPort = 6000;          // default fog node port
  cmd.AddValue("fogHost", "Hostname of the fog node", fogHost);
  cmd.AddValue("fogPort", "Port number of the fog node", fogPort);
  cmd.Parse(argc, argv);

  Time::SetResolution(Time::NS);
  LogComponentEnable("IoTDataSimulation", LOG_LEVEL_INFO);

  uint32_t numIoTDevices = 1000;
  NodeContainer nodes;
  nodes.Create(numIoTDevices);

  // install the Internet protocol stack
  InternetStackHelper stack;
  stack.Install(nodes);

  NS_LOG_INFO("Attempting to resolve fog host: " << fogHost);
  Ipv4Address fogIpAddr = ResolveHostname(fogHost);
  NS_LOG_INFO("Resolved fog host " << fogHost << " to " << fogIpAddr);

  uint32_t packetSize = 1024;
  uint32_t numPackets = 100; 
  Time interval = Seconds(1.0);

  // install IoTDataAPP for each IoT device
  for (uint32_t i = 0; i < nodes.GetN(); ++i) {
    Ptr<IoTDataApp> app = CreateObject<IoTDataApp>();
    app->Setup(fogHost, fogPort, packetSize, numPackets, interval);
    nodes.Get(i)->AddApplication(app);
    app->SetStartTime(Seconds(2.0 + 0.1 * i));
    app->SetStopTime(Seconds(20.0));
  }

  Simulator::Stop(Seconds(25.0));
  Simulator::Run();
  Simulator::Destroy();

  return 0;
}
