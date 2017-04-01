import math
import os.path
import operator

import matplotlib.pyplot as plt
import networkx as nx

class GraphMap:
    def __init__(self, nodes, triangles, cache=False):
        """
        nodes represent the (x, y) address of nodes in the graph.
        triangles give the 3 positions in nodes array to form a triangle.
        """
        self._cache = cache
        self._cache_path = '/tmp/graphmap.data'

        self._graph = None
        if self._cache and os.path.exists(self._cache_path):
            self._graph = self.__read_cache()
        else:
            self.__build_graph_from_mesh(nodes, triangles)

    def display(self):
        node_color = list(nx.get_node_attributes(self._graph, 'color').values())
        edge_color = list(nx.get_edge_attributes(self._graph, 'color').values())
        nx.draw_networkx(self._graph, nx.get_node_attributes(self._graph, 'pos'),
                         node_size=20, with_labels=True, edge_color=edge_color,
                         node_color=node_color)
        plt.show()

    def save(self):
        nx.write_gpickle(self._graph, self._cache_path)

    def get_neirest_node_pos(self, point, direction):
        """
        Get the neirest node position according to the direction.
        """
        best_matches = []
        for node in self._graph.nodes():
            node_pos = self._graph.node[node]['pos']
            dist_point = self.__distance_btw_points(point, node_pos)
            dist_dest = self.__distance_btw_points(direction, node_pos)
            if dist_point < 30:
                best_matches.append({'dist_point': dist_point,
                                     'dist_dest': dist_dest,
                                     'node': node})
        return sorted(best_matches, key=operator.itemgetter('dist_dest'))[0]['node']

    def get_path(self, robot_pos, target, display=False):
        START_NODE_ID = 1000
        END_NODE_ID = 1001

        start_node = self.get_neirest_node_pos(robot_pos['point'], target['point'])
        end_node = self.get_neirest_node_pos(target['point'], robot_pos['point'])

        # TODO: remove edge added to the process before looking for the shortest path.
        # This could give unvalid result.
        path = nx.shortest_path(self._graph, source=start_node, target=end_node, weight='weight')

        self._graph.add_node(START_NODE_ID, pos=robot_pos['point'], color='green')
        self._graph.add_node(END_NODE_ID, pos=target['point'], color='green')

        if display:
            self._graph.add_edge(START_NODE_ID, path[0], color='green')
            self._graph.add_edge(path[-1], END_NODE_ID, color='green')
            for i in range(len(path) - 1):
                self._graph.edge[path[i]][path[i+1]]['color'] = 'green'

        # Add dummy point to represent the node to begin the conversion.
        path = [START_NODE_ID] + path
        path.append(END_NODE_ID)
        return self.__convert_nodelist_to_instruction(path, robot_pos['angle'], target['angle'])

    def __simplify_turn_angle(self, angle):
        if abs(angle) > 180:
            sign = 1 if angle > 0 else -1
            angle = -sign*(360 - abs(angle))
        return round(angle)

    def __convert_nodelist_to_instruction(self, path, robot_angle, target_angle):
        actions = []

        start_angle_constrain = self.__get_node_angle(path[0], path[1])
        actions.append({'action': 'turn', 'value': self.__simplify_turn_angle(start_angle_constrain - robot_angle)})

        for i in range(len(path) - 2):
            distance = self.__distance_btw_points(
                    self._graph.node[path[i]]['pos'],
                    self._graph.node[path[i+1]]['pos']
            )
            actions.append({'action': 'move', 'value': int(distance)})

            # Get the opposite point to calculate the turn angle.
            node_pos = self._graph.node[path[i]]['pos']
            center_pos = self._graph.node[path[i+1]]['pos']
            opposite_pos = (center_pos[0]+(center_pos[0]-node_pos[0]),
                    center_pos[1] + (center_pos[1]-node_pos[1]))
            angle1 = self.__get_pos_angle(self._graph.node[path[i+1]]['pos'], opposite_pos)
            angle2 = self.__get_pos_angle(self._graph.node[path[i+1]]['pos'],
                    self._graph.node[path[i+2]]['pos'])
            turn_angle = self.__simplify_turn_angle(angle2 - angle1)
            if turn_angle != 0:
                actions.append({'action': 'turn', 'value': turn_angle})

        # Finalize the last moving and turning.
        distance = self.__distance_btw_points(
            self._graph.node[path[-2]]['pos'],
            self._graph.node[path[-1]]['pos']
        )
        actions.append({'action': 'move', 'value': int(distance)})

        end_robot_angle = self.__get_node_angle(path[-1], path[-2])
        actions.append({'action': 'turn', 'value': self.__simplify_turn_angle(end_robot_angle -
            target_angle)})

        return actions

    def __clean_actions(self, actions):
        cleaned_actions = []
        for i in range(len(actions) - 2):
            a1 = actions[i]
            a2 = actions[i+1]
            a3 = actions[i+2]

            if a1['action'] == 'turn' and a3['action'] == 'turn':
                if a1['value'] - a2['value'] < 10:
                    # TODO: simplify!
                    pass
                else:
                    cleaned_actions += [a1, a2, a3]
            else if a1['action'] == a2['action'] && a1['action'] == 'move':
                cleaned_actions.append({'action': 'move', 'value': a1['value'] + a2['value']})
        return cleaned_actions

    def __read_cache(self):
        return nx.read_gpickle(self._cache_path)

    def __build_graph_from_mesh(self, nodes, triangle_cells):
        graph = nx.Graph()
        for i, n in enumerate(nodes):
            graph.add_node(i, pos=n, color='red')

        for conns in triangle_cells:
            for i, c in enumerate(conns):
                p1 = c
                p2 = conns[(i+1) % 3]

                weight = self.__distance_btw_points(
                        graph.node[p1]['pos'],
                        graph.node[p2]['pos']
                )
                graph.add_edge(p1, p2, weight=weight, color='black')

        self._graph = graph
        self.__mark_nodes_as_border()
        self.__clean()

        if self._cache:
            self.save()

    def __distance_btw_points(self, p1, p2):
        x = (p1[0] - p2[0])**2
        y = (p1[1] - p2[1])**2
        return math.sqrt(x + y)

    def __merge_nodes(self, node, old_node):
        if node == old_node:
            return
        out_edge_node = self._graph.neighbors(node)
        out_edge_old_node = self._graph.neighbors(old_node)

        for edge in out_edge_old_node:
            if edge not in out_edge_node:
                weight = self.__distance_btw_points(
                    self._graph.node[node]['pos'],
                    self._graph.node[edge]['pos']
                )
                self._graph.add_edge(node, edge, weight=weight, color='black')

        self._graph.remove_node(old_node)

    def __mark_nodes_as_border(self):
        """
        Flag nodes when they are in the borders.
        Moslty works.
        """
        for node in self._graph.nodes():
            out_edges = self._graph.neighbors(node)
            if len(out_edges) == 2 or len(out_edges) == 1:
                self._graph.node[node]['color'] = 'blue'
                self._graph.node[node]['mesh_edge'] = True
                continue

            angles = sorted(self.__get_neighbors_angle(node),
                            key=lambda k: k['angle'])

            biggest_angle = 0
            for i in range(len(angles)):
                a1 = angles[i]['angle']
                a2 = angles[(i+1) % len(angles)]['angle']

                a_diff = (a2 - a1)
                if a_diff < 0:
                    a_diff += 360
                if abs(a_diff) > biggest_angle:
                    biggest_angle = abs(a_diff)
            if biggest_angle > 105:
                self._graph.node[node]['color'] = 'blue'
                self._graph.node[node]['mesh_edge'] = True

    def __get_pos_angle(self, center, node, upper=(0, 0)):
        if upper == (0, 0):
            upper = (2000, center[1])

        a = self.__distance_btw_points(center, node)
        b = self.__distance_btw_points(center, upper)
        c = self.__distance_btw_points(node, upper)

        # Law of cosine
        cosinelaw = (a**2 + b**2 - c**2) / (2*a*b)
        # Clamp the value between [-1; 1] because of inaccuracy in
        # floating point numbers.
        cosinelaw = max(min(cosinelaw, 1.0), -1.0)
        angle = math.degrees(math.acos(cosinelaw))
        # Check if we have passed the 180 degrees or not.
        xpos1 = node[1] - center[1]
        if xpos1 > 0:
            angle = 360 - angle

        return angle


    def __get_node_angle(self, center, node):
        """
        The angle is the absolute angle relative to the X axis.
        """
        center_pos = self._graph.node[center]['pos']
        point_pos = self._graph.node[node]['pos']
        return self.__get_pos_angle(center_pos, point_pos)


    def __get_neighbors_angle(self, node_id):
        neighbors = self._graph.neighbors(node_id)

        data = []
        for i in neighbors:
            data.append({'neighbor': i, 'angle': self.__get_node_angle(node_id, i)})

        return data

    # Remove useless nodes
    def __clean(self):
        for i in range(300):
            for e in self._graph.edges():
                if e[0] == e[1]:
                    continue
                if self._graph[e[0]][e[1]]['weight'] < 7:
                    self.__merge_nodes(e[0], e[1])
                    break
