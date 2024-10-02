import networkx as nx
import matplotlib.pyplot as plt
import random
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from textblob import TextBlob
import hashlib
from community import community_louvain

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

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

class MisinformationAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.messages = []
        self.stop_words = set(stopwords.words('english'))
        self.misinformation_keywords = set(['fake', 'hoax', 'conspiracy', 'scam', 'misleading'])
        self.communities = None

    def generate_simulated_network(self, username):
        seed = int(hashlib.md5(username.encode()).hexdigest(), 16) % (10 ** 8)
        random.seed(seed)

        followers_count = random.randint(10, 1000)
        following_count = random.randint(10, 500)

        self.graph.clear()
        self.graph.add_node(username, followers_count=followers_count, following_count=following_count)

        for i in range(followers_count):
            follower = f"follower_{i}"
            self.graph.add_edge(follower, username)

        for i in range(following_count):
            following = f"following_{i}"
            self.graph.add_edge(username, following)

        for _ in range(min(followers_count, following_count) // 2):
            follower = random.choice(list(self.graph.predecessors(username)))
            following = random.choice(list(self.graph.successors(username)))
            if not self.graph.has_edge(follower, following):
                self.graph.add_edge(follower, following)

       # print(f" {username} with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")

    def get_network_stats(self, username):
        followers = list(self.graph.predecessors(username))
        following = list(self.graph.successors(username))
        return {
            'direct_connections': len(followers) + len(following),
            'followers': len(followers),
            'following': len(following),
            'total_network_size': self.graph.number_of_nodes()
        }

    def visualize_ego_network(self, username, depth=1):
        ego_graph = nx.ego_graph(self.graph, username, radius=depth)
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(ego_graph)
        nx.draw(ego_graph, pos, with_labels=True, node_color='lightblue', 
                node_size=500, font_size=10, font_weight='bold')
        nx.draw_networkx_nodes(ego_graph, pos, nodelist=[username], 
                               node_color='red', node_size=700)
        plt.title(f"Ego Network for User {username} (Depth {depth})")
        plt.savefig(f"ego_network_{username}.png")
        plt.close()

    def detect_communities(self):
        undirected_graph = self.graph.to_undirected()
        self.communities = community_louvain.best_partition(undirected_graph)
        return self.communities

    def get_community_stats(self, username):
        if self.communities is None:
            self.detect_communities()

        user_community = self.communities[username]
        connected_communities = set()
        nodes_in_user_community = 0
        directly_connected_nodes = 0

        for node, community in self.communities.items():
            if community == user_community:
                nodes_in_user_community += 1
            if self.graph.has_edge(username, node) or self.graph.has_edge(node, username):
                connected_communities.add(community)
                directly_connected_nodes += 1

        return {
            'total_communities': len(set(self.communities.values())),
            'user_community_size': nodes_in_user_community,
            'connected_communities': len(connected_communities),
            'directly_connected_nodes': directly_connected_nodes
        }

    def visualize_communities(self, username):
        if self.communities is None:
            self.detect_communities()

        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.graph)
        
        nx.draw_networkx_nodes(self.graph, pos, node_color=list(self.communities.values()), 
                               cmap=plt.cm.get_cmap("Set3"), node_size=100)
        nx.draw_networkx_edges(self.graph, pos, alpha=0.5)
        nx.draw_networkx_nodes(self.graph, pos, nodelist=[username], 
                               node_color='red', node_size=200)

        plt.title(f"Network Communities (User: {username})")
        plt.axis('off')
        plt.savefig(f"community_network_{username}.png")
        plt.close()

    def analyze_message(self, message):
        tokens = word_tokenize(message.lower())
        filtered_tokens = [word for word in tokens if word not in self.stop_words]
        misinformation_score = sum(1 for word in filtered_tokens if word in self.misinformation_keywords)
        return misinformation_score / len(filtered_tokens) if filtered_tokens else 0

    def get_sentiment(self, message):
        analysis = TextBlob(message)
        return analysis.sentiment.polarity

    def propagate_message(self, message, start_node):
        nodes_to_process = [start_node]
        affected_nodes = set([start_node])

        while nodes_to_process:
            current_node = nodes_to_process.pop(0)
            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in affected_nodes and random.random() < 0.3:  # 30% chance of sharing
                    message.increment_share_count()
                    nodes_to_process.append(neighbor)
                    affected_nodes.add(neighbor)

        return affected_nodes

    def is_misinformation(self, message, spread_percentage):
        misinfo_pattern = re.compile(r'\b(fake|hoax|conspiracy)\b')
        return bool(misinfo_pattern.search(message.get_content())) or spread_percentage > 0.1

    def calculate_potential_impact(self, username):
        ego_graph = nx.ego_graph(self.graph, username, radius=2)
        return len(ego_graph.nodes()) / self.graph.number_of_nodes()

    def analyze_message_impact(self, username, message_content):
        message = Message(len(self.messages), message_content, username)
        self.messages.append(message)

        affected_nodes = self.propagate_message(message, username)
        spread_percentage = len(affected_nodes) / self.graph.number_of_nodes()

        misinformation_score = self.analyze_message(message_content)
        sentiment = self.get_sentiment(message_content)
        potential_impact = self.calculate_potential_impact(username)

        print(f"\nMessage Analysis:")
        print(f"Content: {message_content}")
        print(f"Misinformation Score: {misinformation_score:.2f}")
        print(f"Sentiment: {sentiment:.2f}")
        print(f"Affected nodes: {len(affected_nodes)}")
        print(f"Spread percentage: {spread_percentage * 100:.2f}%")
        print(f"Potential impact (reach): {potential_impact * 100:.2f}%")

        if self.is_misinformation(message, spread_percentage):
            print("Warning: This message has been flagged as potential misinformation.")
        else:
            print("This message has not been flagged as misinformation.")

        return {
            'misinformation_score': misinformation_score,
            'sentiment': sentiment,
            'affected_nodes': len(affected_nodes),
            'spread_percentage': spread_percentage,
            'potential_impact': potential_impact
        }

def main():
    analyzer = MisinformationAnalyzer()

    while True:
        username = input("\nEnter a username: ")
        if username.lower() == 'quit':
            break

        analyzer.generate_simulated_network(username)
        
        network_stats = analyzer.get_network_stats(username)
        print("\nNetwork Statistics:")
        print(f"Direct connections: {network_stats['direct_connections']}")
        print(f"Followers: {network_stats['followers']}")
        print(f"Following: {network_stats['following']}")
        print(f"Total network size: {network_stats['total_network_size']}")

        analyzer.visualize_ego_network(username, depth=2)
        print(f"Ego network visualization saved as ego_network_{username}.png")

        community_stats = analyzer.get_community_stats(username)
        print("\nCommunity Statistics:")
        print(f"Total number of communities: {community_stats['total_communities']}")
        print(f"Size of user's community: {community_stats['user_community_size']}")
        print(f"Number of directly connected communities: {community_stats['connected_communities']}")
        print(f"Total number of directly connected nodes: {community_stats['directly_connected_nodes']}")

        analyzer.visualize_communities(username)
        print(f"Community visualization saved as community_network_{username}.png")

        potential_impact = analyzer.calculate_potential_impact(username)
        print(f"\nPotential Impact (Reach) in Network: {potential_impact * 100:.2f}%")

        while True:
            message_content = input("Write a message and enter to send(Post): ")
            if message_content.lower() == 'q':
                break

            impact = analyzer.analyze_message_impact(username, message_content)

            if impact['misinformation_score'] > 0.1:
                print("\nAdvice: This message contains potential misinformation. Verify the information before sharing.")
            else:
                print("\nAdvice: While this message doesn't appear to contain obvious misinformation, always critically evaluate information before sharing.")

   
if __name__ == "__main__":
    main()