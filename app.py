import threading
from typing import Any, Optional
import matplotlib.pyplot as plt
import networkx as nx
from flask import Flask, render_template, request, jsonify
import time
import random

class Node:
    def __init__(self, key: Any):
        self.key = key
        self.next = None
        self.marked = False

class NonBlockingLinkedList:
    def __init__(self):
        self.head = Node(float('-inf'))
        self.tail = Node(float('inf'))
        self.head.next = self.tail

    def search(self, key: Any) -> tuple[Node, Node]:
        while True:
            pred = self.head
            curr = pred.next
            while curr.key < key:
                if curr.marked:
                    if not pred.next.compare_exchange_strong(curr, curr.next):
                        break
                    curr = curr.next
                else:
                    pred = curr
                    curr = curr.next
            if not curr.marked:
                return pred, curr

    def insert(self, key: Any) -> bool:
        new_node = Node(key)
        while True:
            pred, curr = self.search(key)
            if curr.key == key:
                return False
            new_node.next = curr
            if pred.next.compare_exchange_strong(curr, new_node):
                return True

    def delete(self, key: Any) -> bool:
        while True:
            pred, curr = self.search(key)
            if curr.key != key:
                return False
            succ = curr.next
            if not curr.marked:
                if curr.marked.compare_exchange_strong(False, True):
                    if pred.next.compare_exchange_strong(curr, succ):
                        return True
                    else:
                        self.search(key)
                        return True
            else:
                self.search(key)

    def contains(self, key: Any) -> bool:
        curr = self.head
        while curr.key < key:
            curr = curr.next
        return curr.key == key and not curr.marked

    def to_list(self) -> list:
        result = []
        curr = self.head.next
        while curr != self.tail:
            if not curr.marked:
                result.append(curr.key)
            curr = curr.next
        return result

def visualize_list(linked_list: NonBlockingLinkedList):
    G = nx.DiGraph()
    node_labels = {}
    curr = linked_list.head
    index = 0
    while curr:
        G.add_node(index)
        node_labels[index] = str(curr.key)
        if index > 0:
            G.add_edge(index-1, index)
        curr = curr.next
        index += 1

    pos = nx.spring_layout(G)
    plt.figure(figsize=(12, 4))
    nx.draw(G, pos, with_labels=False, node_color='lightblue', node_size=500, arrows=True)
    nx.draw_networkx_labels(G, pos, node_labels, font_size=10)
    plt.title("Non-Blocking Linked List Visualization")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig('static/list_visualization.png')
    plt.close()

app = Flask(__name__)

linked_list = NonBlockingLinkedList()
operation_times = {'insert': [], 'delete': [], 'contains': []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_test', methods=['POST'])
def run_test():
    num_threads = int(request.form['num_threads'])
    num_operations = int(request.form['num_operations'])

    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=perform_operations, args=(num_operations,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    visualize_list(linked_list)

    return jsonify({
        'list_contents': linked_list.to_list(),
        'operation_times': operation_times
    })

def perform_operations(num_operations):
    for _ in range(num_operations):
        operation = random.choice(['insert', 'delete', 'contains'])
        key = random.randint(1, 100)

        start_time = time.time()
        if operation == 'insert':
            linked_list.insert(key)
        elif operation == 'delete':
            linked_list.delete(key)
        else:
            linked_list.contains(key)
        end_time = time.time()

        operation_times[operation].append((end_time - start_time) * 1000)  # Convert to milliseconds

if __name__ == '__main__':
    app.run(debug=True)