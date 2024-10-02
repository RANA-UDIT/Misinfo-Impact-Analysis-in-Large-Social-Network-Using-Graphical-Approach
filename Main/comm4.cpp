#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <unordered_map>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

class Graph {
private:
    std::vector<std::vector<int>> adjacencyList;
    std::vector<int> nodeDegrees;
    long long totalEdges = 0;
    int numNodes = 0;

public:
    void addEdge(int from, int to) {
        if (from >= numNodes || to >= numNodes) {
            numNodes = std::max(numNodes, std::max(from, to) + 1);
            adjacencyList.resize(numNodes);
            nodeDegrees.resize(numNodes, 0);
        }
        adjacencyList[from].push_back(to);
        adjacencyList[to].push_back(from);
        nodeDegrees[from]++;
        nodeDegrees[to]++;
        totalEdges++;
    }

    const std::vector<int>& getNeighbors(int node) const {
        return adjacencyList[node];
    }

    int getDegree(int node) const {
        return nodeDegrees[node];
    }

    long long getTotalEdges() const {
        return totalEdges;
    }

    int getNumNodes() const {
        return numNodes;
    }
};

class LouvainCommunityDetection {
private:
    Graph graph;
    std::vector<int> communities;

    int countCommunities() const {
        std::unordered_map<int, bool> seen_communities;
        for (int community : communities) {
            seen_communities[community] = true;
        }
        return seen_communities.size();
    }

public:
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

        int numNodes = graph.getNumNodes();
        communities.resize(numNodes);
        for (int i = 0; i < numNodes; i++) {
            communities[i] = i;
        }
    }

    std::pair<int, int> detectCommunities() {
        int numNodes = graph.getNumNodes();
        const int maxIterations = 20;  // Reduced number of iterations
        std::vector<int> communityCount(maxIterations + 1, 0);

        std::random_device rd;
        std::mt19937 g(rd());

        for (int iteration = 0; iteration <= maxIterations; iteration++) {
            bool improvement = false;
            std::vector<int> nodes(numNodes);
            for (int i = 0; i < numNodes; i++) nodes[i] = i;
            std::shuffle(nodes.begin(), nodes.end(), g);

            for (int v : nodes) {
                int old_community = communities[v];
                std::unordered_map<int, int> community_connections;

                for (int nbr : graph.getNeighbors(v)) {
                    community_connections[communities[nbr]]++;
                }

                int best_community = old_community;
                int max_connections = 0;
                for (const auto& entry : community_connections) {
                    if (entry.second > max_connections) {
                        max_connections = entry.second;
                        best_community = entry.first;
                    }
                }

                if (best_community != old_community) {
                    communities[v] = best_community;
                    improvement = true;
                }
            }

            communityCount[iteration] = countCommunities();

            if (!improvement) break;
        }

        int bestIteration = 0;
        int minCommunities = numNodes;
        for (int i = 0; i <= maxIterations; i++) {
            if (communityCount[i] < minCommunities && communityCount[i] > 0) {
                minCommunities = communityCount[i];
                bestIteration = i;
            }
        }

        return std::make_pair(bestIteration, minCommunities);
    }
};

int main() {
    LouvainCommunityDetection lcd;
    lcd.loadGraph("sample_graph1000.txt");

    auto start = std::chrono::high_resolution_clock::now();
    auto result = lcd.detectCommunities();
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> execution_time = end - start;

    std::cout << "Best number of iterations: " << result.first << std::endl;
    std::cout << "Number of communities detected: " << result.second << std::endl;
    std::cout << "Execution time: " << execution_time.count() << " seconds" << std::endl;

    return 0;
}