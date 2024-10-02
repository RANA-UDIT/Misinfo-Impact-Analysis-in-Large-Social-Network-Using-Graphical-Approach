#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <unordered_map>
#include <cmath>
#include <algorithm>
#include <omp.h>
#include <chrono>
#include <set>
#include <string>
#include <random>
#include <queue>
#include <regex>

class Graph {
private:
    std::unordered_map<int, std::vector<int>> adjacencyList;
    std::unordered_map<int, double> nodeDegrees;
    double totalEdges = 0;

public:
    void addEdge(int from, int to) {
        adjacencyList[from].push_back(to);
        adjacencyList[to].push_back(from);
        nodeDegrees[from]++;
        nodeDegrees[to]++;
        totalEdges++;
    }

    std::vector<int> getNeighbors(int node) {
        return adjacencyList[node];
    }

    double getDegree(int node) {
        return nodeDegrees[node];
    }

    double getTotalEdges() {
        return totalEdges;
    }

    std::vector<int> getNodes() {
        std::vector<int> nodes;
        for (const auto& pair : adjacencyList) {
            nodes.push_back(pair.first);
        }
        return nodes;
    }
};

class Message {
public:
    enum class State { CREATED, SHARED, VIRAL, FLAGGED };
    
    Message(int id, const std::string& content, int sourceNode)
        : id(id), content(content), sourceNode(sourceNode), state(State::CREATED), shareCount(0) {}
    
    int getId() const { return id; }
    const std::string& getContent() const { return content; }
    int getSourceNode() const { return sourceNode; }
    State getState() const { return state; }
    int getShareCount() const { return shareCount; }
    
    void incrementShareCount() { 
        shareCount++; 
        updateState();
    }
    
    void flagAsMisinformation() { state = State::FLAGGED; }

private:
    int id;
    std::string content;
    int sourceNode;
    State state;
    int shareCount;
    
    void updateState() {
        if (shareCount > 100) state = State::VIRAL;
        else if (shareCount > 10) state = State::SHARED;
    }
};

class LouvainCommunityDetection {
private:
    Graph graph;
    std::vector<int> communities;
    double modularity;
    std::vector<Message> messages;
    std::mt19937 rng;

    double calculateModularity() {
        std::vector<double> communityInternalEdges(communities.size(), 0);
        std::vector<double> communityTotalEdges(communities.size(), 0);
        double m = graph.getTotalEdges();
        double Q = 0;

        #pragma omp parallel for
        for (int i = 0; i < graph.getNodes().size(); i++) {
            int node = graph.getNodes()[i];
            int comm = communities[node];
            double nodeDegree = graph.getDegree(node);

            #pragma omp atomic
            communityTotalEdges[comm] += nodeDegree;

            for (int neighbor : graph.getNeighbors(node)) {
                if (communities[neighbor] == comm) {
                    #pragma omp atomic
                    communityInternalEdges[comm] += 1;
                }
            }
        }

        for (int i = 0; i < communities.size(); i++) {
            if (communityTotalEdges[i] > 0) {
                Q += (communityInternalEdges[i] / (2 * m)) - std::pow(communityTotalEdges[i] / (2 * m), 2);
            }
        }

        return Q;
    }

    void moveNode(int node) {
        int currentCommunity = communities[node];
        std::unordered_map<int, double> communityGains;

        for (int neighbor : graph.getNeighbors(node)) {
            int neighborCommunity = communities[neighbor];
            if (communityGains.find(neighborCommunity) == communityGains.end()) {
                communityGains[neighborCommunity] = 0;
            }
            communityGains[neighborCommunity] += 1;
        }

        int bestCommunity = currentCommunity;
        double bestGain = 0;

        for (const auto& pair : communityGains) {
            int community = pair.first;
            double gain = pair.second - (graph.getDegree(node) * communityGains[community] / (2 * graph.getTotalEdges()));
            if (gain > bestGain) {
                bestGain = gain;
                bestCommunity = community;
            }
        }

        if (bestCommunity != currentCommunity) {
            communities[node] = bestCommunity;
        }
    }

public:
    LouvainCommunityDetection() : rng(std::random_device{}()) {}

    void loadGraph(const std::string& filename) {
        std::ifstream file(filename);
        std::string line;

        while (std::getline(file, line)) {
            if (line[0] == '#') continue;
            std::istringstream iss(line);
            int from, to;
            if (iss >> from >> to) {
                graph.addEdge(from, to);
            }
        }

        communities.resize(graph.getNodes().size());
        for (int i = 0; i < graph.getNodes().size(); i++) {
            communities[i] = i;
        }
    }

    int detectCommunities(bool useParallel = false) {
        bool improvement = true;
        while (improvement) {
            improvement = false;
            if (useParallel) {
                #pragma omp parallel for schedule(dynamic)
                for (int i = 0; i < graph.getNodes().size(); i++) {
                    int node = graph.getNodes()[i];
                    int oldCommunity = communities[node];
                    moveNode(node);
                    if (communities[node] != oldCommunity) {
                        #pragma omp atomic write
                        improvement = true;
                    }
                }
            } else {
                for (int node : graph.getNodes()) {
                    int oldCommunity = communities[node];
                    moveNode(node);
                    if (communities[node] != oldCommunity) {
                        improvement = true;
                    }
                }
            }
        }

        modularity = calculateModularity();

        std::unordered_map<int, int> uniqueCommunities;
        for (int community : communities) {
            uniqueCommunities[community] = 1;
        }

        return uniqueCommunities.size();
    }

    double getModularity() {
        return modularity;
    }

    struct NodeInfo {
        int community;
        std::set<int> connectedCommunities;
        std::vector<int> directlyConnectedNodes;
        std::set<int> allConnectedNodes;
    };

    NodeInfo getNodeInfo(int targetNode) {
        NodeInfo info;
        info.community = communities[targetNode];

        std::set<int> visited;
        std::vector<int> queue;

        queue.push_back(targetNode);
        visited.insert(targetNode);

        while (!queue.empty()) {
            int currentNode = queue.front();
            queue.erase(queue.begin());

            for (int neighbor : graph.getNeighbors(currentNode)) {
                if (currentNode == targetNode) {
                    info.directlyConnectedNodes.push_back(neighbor);
                }

                info.connectedCommunities.insert(communities[neighbor]);
                info.allConnectedNodes.insert(neighbor);

                if (visited.find(neighbor) == visited.end()) {
                    visited.insert(neighbor);
                    queue.push_back(neighbor);
                }
            }
        }

        return info;
    }

    void initiateMessage(int sourceNode, const std::string& content) {
        messages.emplace_back(messages.size(), content, sourceNode);
        propagateMessage(messages.back());
    }
    
    std::set<int> propagateMessage(const Message& message, int startNode = -1) {
        std::queue<int> nodesToProcess;
        std::set<int> affectedNodes;
        
        if (startNode == -1) {
            startNode = message.getSourceNode();
        }
        
        nodesToProcess.push(startNode);
        affectedNodes.insert(startNode);
        
        while (!nodesToProcess.empty()) {
            int currentNode = nodesToProcess.front();
            nodesToProcess.pop();
            
            for (int neighbor : graph.getNeighbors(currentNode)) {
                if (affectedNodes.count(neighbor) == 0 && shouldShareMessage()) {
                    messages[message.getId()].incrementShareCount();
                    nodesToProcess.push(neighbor);
                    affectedNodes.insert(neighbor);
                }
            }
        }
        
        return affectedNodes;
    }
    
    bool shouldShareMessage() {
        std::uniform_real_distribution<> dis(0.0, 1.0);
        return dis(rng) < 0.3; // 30% chance of sharing
    }
    
    bool isMisinformation(const Message& message, double spreadPercentage) {
        static const std::regex misinfoPattern("\\b(fake|hoax|conspiracy)\\b");
        return std::regex_search(message.getContent(), misinfoPattern) || spreadPercentage > 0.1; // 10% threshold
    }
    
    void analyzeMessageImpact(int targetNode, const std::string& messageContent = "") {
        std::string content = messageContent.empty() ? "Sample message from target node" : messageContent;
        Message targetMessage(messages.size(), content, targetNode);
        messages.push_back(targetMessage);
        
        std::set<int> affectedNodes = propagateMessage(targetMessage, targetNode);
        double spreadPercentage = static_cast<double>(affectedNodes.size()) / graph.getNodes().size();
        
        std::cout << "Message from target node " << targetNode << ":" << std::endl;
        std::cout << "Content: " << content << std::endl;
        std::cout << "Affected nodes: " << affectedNodes.size() << std::endl;
        std::cout << "Spread percentage: " << spreadPercentage * 100 << "%" << std::endl;
        
        if (isMisinformation(targetMessage, spreadPercentage)) {
            std::cout << "This message has been flagged as potential misinformation." << std::endl;
        } else {
            std::cout << "This message has not been flagged as misinformation." << std::endl;
        }
        
        // Check if the target node has any flagged misinformation messages
        bool hasMisinfoMessage = false;
        for (const auto& message : messages) {
            if (message.getSourceNode() == targetNode && message.getState() == Message::State::FLAGGED) {
                hasMisinfoMessage = true;
                break;
            }
        }
        
        std::cout << "Target node " << (hasMisinfoMessage ? "has" : "does not have") << " flagged misinformation messages." << std::endl;
    }
};

int main() {
    LouvainCommunityDetection lcd;
    lcd.loadGraph("sample_graph1500.txt");

    // Parallel execution
    auto start_parallel = std::chrono::high_resolution_clock::now();
    int numCommunitiesParallel = lcd.detectCommunities(true);
    auto end_parallel = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> parallel_time = end_parallel - start_parallel;

    std::cout << "Number of communities detected: " << numCommunitiesParallel << std::endl;
    std::cout << "Parallel execution time: " << parallel_time.count() << " seconds" << std::endl;

    // Initiate some sample messages
    lcd.initiateMessage(1, "This is a normal message.");
    lcd.initiateMessage(10, "FAKE: Earth is flat! Share this conspiracy theory!");
    lcd.initiateMessage(100, "COVID-19 vaccine contains microchips. This is a hoax!");

    // Get target node from user
    int targetNode;
    std::cout << "\nEnter a target node: ";
    std::cin >> targetNode;

    // Get message content from user (optional)
    std::string messageContent;
    std::cout << "Enter a message for the target node (press Enter for default): ";
    std::cin.ignore();
    std::getline(std::cin, messageContent);

    // Analyze message impact from target node
    lcd.analyzeMessageImpact(targetNode, messageContent);

    // Get and display node information
    LouvainCommunityDetection::NodeInfo nodeInfo = lcd.getNodeInfo(targetNode);

    std::cout << "\nTarget Node: " << targetNode << std::endl;
    std::cout << "Community: " << nodeInfo.community << std::endl;
    std::cout << "Number of connected communities: " << nodeInfo.connectedCommunities.size() << std::endl;
    std::cout << "Number of directly connected nodes: " << nodeInfo.directlyConnectedNodes.size() << std::endl;
    std::cout << "Total number of connected nodes from all communities: " << nodeInfo.allConnectedNodes.size() << std::endl;

    std::cout << "Directly connected nodes: ";
    for (int node : nodeInfo.directlyConnectedNodes) {
        std::cout << node << " ";
    }
    std::cout << std::endl;

    return 0;
}