import networkx as nx
from collections import defaultdict
import random
import time
import re

class Graph:
    def __init__(self):
        self.adjacency_list = defaultdict(list)
        self.node_degrees = defaultdict(float)
        self.total_edges = 0

    def add_edge(self, from_node, to_node):
        self.adjacency_list[from_node].append(to_node)
        self.adjacency_list[to_node].append(from_node)
        self.node_degrees[from_node] += 1
        self.node_degrees[to_node] += 1
        self.total_edges += 1

    def get_neighbors(self, node):
        return self.adjacency_list[node]

    def get_degree(self, node):
        return self.node_degrees[node]

    def get_total_edges(self):
        return self.total_edges

    def get_nodes(self):
        return list(self.adjacency_list.keys())

class Message:
    class State:
        CREATED = 0
        SHARED = 1
        VIRAL = 2
        FLAGGED = 3

    def __init__(self, id, content, source_node):
        self.id = id
        self.content = content
        self.source_node = source_node
        self.state = self.State.CREATED
        self.share_count = 0

    def get_id(self):
        return self.id

    def get_content(self):
        return self.content

    def get_source_node(self):
        return self.source_node

    def get_state(self):
        return self.state

    def get_share_count(self):
        return self.share_count

    def increment_share_count(self):
        self.share_count += 1
        self.update_state()

    def flag_as_misinformation(self):
        self.state = self.State.FLAGGED

    def update_state(self):
        if self.share_count > 100:
            self.state = self.State.VIRAL
        elif self.share_count > 10:
            self.state = self.State.SHARED

class LouvainCommunityDetection:
    def __init__(self):
        self.graph = Graph()
        self.communities = []
        self.modularity = 0
        self.messages = []
        self.rng = random.Random()

    def calculate_modularity(self):
        community_internal_edges = [0] * len(self.communities)
        community_total_edges = [0] * len(self.communities)
        m = self.graph.get_total_edges()
        Q = 0

        for node in self.graph.get_nodes():
            comm = self.communities[node]
            node_degree = self.graph.get_degree(node)
            community_total_edges[comm] += node_degree

            for neighbor in self.graph.get_neighbors(node):
                if self.communities[neighbor] == comm:
                    community_internal_edges[comm] += 1

        for i in range(len(self.communities)):
            if community_total_edges[i] > 0:
                Q += (community_internal_edges[i] / (2 * m)) - (community_total_edges[i] / (2 * m)) ** 2

        return Q

    def move_node(self, node):
        current_community = self.communities[node]
        community_gains = defaultdict(float)

        for neighbor in self.graph.get_neighbors(node):
            neighbor_community = self.communities[neighbor]
            community_gains[neighbor_community] += 1

        best_community = current_community
        best_gain = 0

        for community, gain in community_gains.items():
            gain -= (self.graph.get_degree(node) * community_gains[community] / (2 * self.graph.get_total_edges()))
            if gain > best_gain:
                best_gain = gain
                best_community = community

        if best_community != current_community:
            self.communities[node] = best_community

    def load_graph(self, filename):
        with open(filename, 'r') as file:
            for line in file:
                if line[0] == '#':
                    continue
                from_node, to_node = map(int, line.split())
                self.graph.add_edge(from_node, to_node)

        self.communities = list(range(len(self.graph.get_nodes())))

    def detect_communities(self, use_parallel=False):
        improvement = True
        while improvement:
            improvement = False
            for node in self.graph.get_nodes():
                old_community = self.communities[node]
                self.move_node(node)
                if self.communities[node] != old_community:
                    improvement = True

        self.modularity = self.calculate_modularity()

        unique_communities = set(self.communities)
        return len(unique_communities)

    def get_modularity(self):
        return self.modularity

    class NodeInfo:
        def __init__(self):
            self.community = 0
            self.connected_communities = set()
            self.directly_connected_nodes = []
            self.all_connected_nodes = set()

    def get_node_info(self, target_node):
        info = self.NodeInfo()
        info.community = self.communities[target_node]

        visited = set()
        queue = [target_node]
        visited.add(target_node)

        while queue:
            current_node = queue.pop(0)
            for neighbor in self.graph.get_neighbors(current_node):
                if current_node == target_node:
                    info.directly_connected_nodes.append(neighbor)

                info.connected_communities.add(self.communities[neighbor])
                info.all_connected_nodes.add(neighbor)

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return info

    def initiate_message(self, source_node, content):
        message = Message(len(self.messages), content, source_node)
        self.messages.append(message)
        self.propagate_message(message)

    def propagate_message(self, message, start_node=-1):
        if start_node == -1:
            start_node = message.get_source_node()

        nodes_to_process = [start_node]
        affected_nodes = set([start_node])

        while nodes_to_process:
            current_node = nodes_to_process.pop(0)
            for neighbor in self.graph.get_neighbors(current_node):
                if neighbor not in affected_nodes and self.should_share_message():
                    self.messages[message.get_id()].increment_share_count()
                    nodes_to_process.append(neighbor)
                    affected_nodes.add(neighbor)

        return affected_nodes

    def should_share_message(self):
        return self.rng.random() < 0.3

    def is_misinformation(self, message, spread_percentage):
        misinfo_pattern = re.compile(r'\b(fake|hoax|conspiracy)\b')
        return bool(misinfo_pattern.search(message.get_content())) or spread_percentage > 0.1

    def analyze_message_impact(self, target_node, message_content=""):
        content = message_content if message_content else "Sample message from target node"
        target_message = Message(len(self.messages), content, target_node)
        self.messages.append(target_message)

        affected_nodes = self.propagate_message(target_message, target_node)
        spread_percentage = len(affected_nodes) / len(self.graph.get_nodes())

        print(f"Message from target node {target_node}:")
        print(f"Content: {content}")
        print(f"Affected nodes: {len(affected_nodes)}")
        print(f"Spread percentage: {spread_percentage * 100}%")

        if self.is_misinformation(target_message, spread_percentage):
            print("This message has been flagged as potential misinformation.")
        else:
            print("This message has not been flagged as misinformation.")

        has_misinfo_message = any(
            message.get_source_node() == target_node and message.get_state() == Message.State.FLAGGED
            for message in self.messages
        )

        print(f"Target node {'has' if has_misinfo_message else 'does not have'} flagged misinformation messages.")

def main():
    lcd = LouvainCommunityDetection()
    lcd.load_graph("sample_graph1500.txt")

    start_time = time.time()
    num_communities = lcd.detect_communities(True)
    end_time = time.time()
    parallel_time = end_time - start_time

    print(f"Number of communities detected: {num_communities}")
    print(f"Parallel execution time: {parallel_time} seconds")

    lcd.initiate_message(1, "This is a normal message.")
    lcd.initiate_message(10, "FAKE: Earth is flat! Share this conspiracy theory!")
    lcd.initiate_message(100, "COVID-19 vaccine contains microchips. This is a hoax!")

    target_node = int(input("\nEnter a target node: "))
    message_content = input("Enter a message for the target node (press Enter for default): ")

    lcd.analyze_message_impact(target_node, message_content)

    node_info = lcd.get_node_info(target_node)

    print(f"\nTarget Node: {target_node}")
    print(f"Community: {node_info.community}")
    print(f"Number of connected communities: {len(node_info.connected_communities)}")
    print(f"Number of directly connected nodes: {len(node_info.directly_connected_nodes)}")
    print(f"Total number of connected nodes from all communities: {len(node_info.all_connected_nodes)}")

    print("Directly connected nodes:", end=" ")
    print(*node_info.directly_connected_nodes)

if __name__ == "__main__":
    main()