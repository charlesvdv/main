import math

import matplotlib.pyplot as plt
import networkx as nx

class GraphMap:
    def __init__(self, nodes, triangle_cells):
        self._graph = self.__build_graph(nodes, triangle_cells)
        self.__clean()

    def display(self):
        nx.draw(self._graph, nx.get_node_attributes(self._graph, 'pos'))
        plt.show()

    def __distance_btw_points(self, p1, p2):
        x = (p1[0] - p2[0])**2
        y = (p1[1] - p2[1])**2
        return math.sqrt(x + y)

    def __build_graph(self, nodes, triangle_cells):
        graph = nx.Graph()
        for i, n in enumerate(nodes):
            graph.add_node(i, pos=n)

        for conns in triangle_cells:
            for i, c in enumerate(conns):
                p1 = c
                p2 = conns[(i+1) % 3]

                weight = self.__distance_btw_points(graph.node[p1]['pos'], graph.node[p2]['pos'])
                graph.add_edge(p1, p2, weight=weight)
        return graph

    def __remove_node(p):
        pass

    def __mark_nodes_as_border(self):
        for node in self._graph.nodes():
            pass

    # Remove useless nodes
    def __clean(self):
        pass
