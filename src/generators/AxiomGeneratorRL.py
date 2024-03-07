import numpy as np

from .aux import *
from src.simplefact import CE
from src.simplefact.syntax import TOP, BOT, NOT, ANY, ALL, AND, OR, SUB, DIS


class AxiomGeneratorRL:
	def __init__(self, *, rng: np.random.Generator, n_atomic: int, p_atomic: float, n_roles: int):
		self.rng = rng
		self.n_atomic = n_atomic
		self.p_atomic = p_atomic
		self.n_roles = n_roles
		assert self.n_roles > 0

	def generate_leaf(self, nested: bool) -> int:
		if self.rng.random() < self.p_atomic:
			return int(self.rng.integers(0, self.n_atomic))
		else:
			if nested:
				return int(self.rng.choice([TOP, BOT]))
			else:
				return BOT

	def generate_unary(self, children, sub: bool, nested: bool) -> CE:
		assert len(children) == 1
		if sub:
			op = ANY
		else:
			op = int(self.rng.choice([NOT, ALL]))
		if op == NOT:
			return op, self._populate_tree(children[0], sub, nested)
		else:
			role = self.rng.integers(0, self.n_roles)
			return op, int(role), self._populate_tree(children[0], sub, True)

	def generate_binary(self, children, sub: bool, nested: bool) -> CE:
		assert len(children) == 2
		if sub:
			op = int(self.rng.choice([AND, OR]))
		else:
			op = AND
		return op, self._populate_tree(children[0], sub, nested), self._populate_tree(children[1], sub, nested)

	def _populate_tree(self, tree: Tree, sub: bool, nested: bool) -> CE:
		assert tree != NODE
		if tree == LEAF:
			return self.generate_leaf(nested)
		else:
			assert is_iterable(tree)
			op, children = tree[0], tree[1:]
			if op == UNARY:
				return self.generate_unary(children, sub, nested)
			elif op == BINARY:
				return self.generate_binary(children, sub, nested)
			else:
				assert False

	def populate_tree(self, tree: Tree) -> CE:
		assert is_iterable(tree)
		assert len(tree) == 3
		op, left, right = tree
		assert op == ROOT, op
		op = int(self.rng.choice([SUB, DIS]))
		left = self._populate_tree(left, True, False)
		right = self._populate_tree(right, op == DIS, False)
		return op, left, right

	def __call__(self, tree: Tree) -> CE:
		return self.populate_tree(tree)
