#!/usr/bin/env python

import time
from collections import deque

'''
To transform traces into CFG:
1) traces -> adjacency matrix
	 
2) adjacency matrix -> graph

'''
class BasicBlockNode:
	''' Basic Block Node (for cfg)'''
	
	def __init__(self, addr = "", ins = 0):
		self.addr = addr 
		self.ins = ins
		self.children = []

	def add_ins(self, ins):
		self.ins += ins

	def add_child(self, child):
		# check if child exists
		for c in self.children:
			if child.addr == c.addr:
				return 1
		self.children.append(child)
		return 0

	def has_children(self):
		return ( len(self.children) > 0 )

	def get_children(self):
		return self.children

	def print_tree(self, depth):
		f = open("tree.txt", "a")
		f.write(str(depth* ' ') + str(self) + "(" + str(depth) + ")\n")
		#print str(depth) + " == " + str(self)
		f.close()
		depth += 1
		children = self.get_children()
		for child in children:
			child.print_tree(depth)

	def __str__(self):
		return "Addr " + str(self.addr) + " ins " + str(self.ins)	

class ControlFlowGraph:
	''' Control Flow Graph composed of basic blocks '''

	def __init__(self, root = ""):
		self.root = root
		self.node_address_set = set()

	def node_exist(self, addr):
		return (addr in self.node_address_set)	

	def find_node(self, addr):
		return self.dfs(addr)
			
	def dfs(self, addr):
		visited = set()
		stack = [self.root]
		while stack:
			node = stack.pop()
			if addr != "" and node.addr == addr:
				return node
			if node.addr not in visited:
				visited.add(node.addr)
			 	stack = stack + list(node.get_children())
		return visited

	def get_max_width(self):
		# essentially run bfs and keep track of maximum width
		visited = set()
		queue = deque()
		queue.append(self.root)
		prev_children_added = 1
		cur_children_added = 0
		max_width = 1
		while queue:
			node = queue.popleft()
			prev_children_added -= 1
			if node.addr not in visited:
				visited.add(node.addr)
				queue.extend(node.get_children())
				cur_children_added = len(node.get_children())
				if prev_children_added == 0:
					# all ndoes from one level have been popped off
					# we can now obtain breadth of next level
					if max_width < len(queue):
						max_width = len(queue)
					# reset cur_children_added
					prev_children_added = len(queue)
					cur_children_added = 0
		return max_width	

	def get_max_depth(self):
		# essentially run bfs and keep track of depth
		visited = set()
		queue = deque([self.root])
		prev_children_added = 1
		cur_children_added = 0
		depth = 0
		while queue:
			node = queue.popleft()
			prev_children_added -= 1
			if node.addr not in visited:
				visited.add(node.addr)
				queue.extend(node.get_children())
				cur_children_added += len(node.get_children())
				if ( prev_children_added == 0 ):
					# all ndoes from one level have been popped off
					# reset cur_children_added
					prev_children_added = cur_children_added
					cur_children_added = 0
					depth += 1
		return (depth-1) # -1 to account for root

	def print_tree(self):
		return self.root.print_tree(0)

	def print_tree_dfs(self):
		queue = deque([self.root])
		visited = set()
		depth = 0
		prev_children_added = 1
		cur_children_added = 0
		dfs = []
		nodes = []
		while queue:
			node = queue.popleft()
			prev_children_added -= 1
			dfs.append(depth)
			try:
				nodes.append(node.addr)
			except AttributeError:
				print "ERROR: Node " + str(node)
			if node.addr not in visited:
				visited.add(node.addr)
				queue.extend(node.get_children())
				cur_children_added += len(node.get_children())
				if ( prev_children_added == 0 ):
					# all ndoes from one level have been popped off
					# reset cur_children_added
					prev_children_added = cur_children_added
					cur_children_added = 0
					depth += 1
		#print dfs
		#print nodes
		#return zip(dfs, nodes)
		return nodes

def create_dict(tree_rep, tree_depth, inputs):
	d = dict()
	d["depth"] = tree_depth
	#d["dfs"] = ",".join(list(map(str, zip(*tree_rep)[0])))
	d["levels"] = ",".join(list(zip(*tree_rep)[1]))
	d["inputs"] = ",".join(inputs)
#	for item in zp:
#		depth = item[0]
#		addr = float(item[1])
#		if depth in d:
#			d[depth] += addr
#		else:
#			d[depth] = addr

	return d


def data_to_graph(lines):
	graph = ControlFlowGraph()
	index = 0

	if len(lines) == 0:
		return None

	for line in lines[1:]:
		text, addr, text2, ins = line.split()
		if index == 0:
			node = BasicBlockNode(addr, int(ins))
			graph.root = node
			graph.node_address_set.add(addr)
		else:
			# check if node already exists in tree
			if graph.node_exist(addr):
				# if yes, find that node and add to its children
				node = graph.find_node(addr)
				node.add_ins(int(ins))
			else:
				# if not, create new node and add it to prev_node's children
				node = BasicBlockNode(addr, int(ins))
				prev_node.add_child(node)
				graph.node_address_set.add(addr)
		prev_node = node
		index += 1
	return graph

def trace_to_graph(trace_file):
	f = open(trace_file, 'r')
	lines = f.readlines()
	f.close()
	return data_to_graph(lines)

def run(trace_file, inputs):
	g = trace_to_graph(trace_file)
	#print g.get_max_depth()
	#print g.get_max_width()
	#return g
	#return create_dict(g.print_tree_dfs(), g.get_max_depth(), inputs)
	g.print_tree()

