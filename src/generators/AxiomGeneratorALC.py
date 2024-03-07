import numpy as np

from src.simplefact import CE
from src.simplefact.syntax import TOP, BOT, NOT, ANY, ALL, AND, OR, SUB, DIS
from .aux import *


class AxiomGeneratorALC:
	def __init__(self, *, rng: np.random.Generator, n_atomic: int, p_atomic: float, n_roles: int):
		self.rng = rng
		self.n_atomic = n_atomic
		self.p_atomic = p_atomic
		self.n_roles = n_roles

	def generate_leaf(self) -> int:
		if self.rng.random() < self.p_atomic:
			return int(self.rng.integers(0, self.n_atomic))
		else:
			return int(self.rng.choice([TOP, BOT]))

	def generate_unary(self) -> tuple[int] | tuple[int, int]:
		if self.n_roles == 0:
			return (NOT,)
		op = int(self.rng.choice([NOT, ANY, ALL]))
		if op == NOT:
			return (op,)
		else:
			role = self.rng.integers(0, self.n_roles)
			return op, int(role)

	def generate_binary(self) -> tuple[int]:
		return (int(self.rng.choice([AND, OR])),)

	def generate_root(self) -> tuple[int]:
		return (int(self.rng.choice([SUB, DIS])),)

	def populate_tree(self, tree: Tree) -> CE:
		assert tree != NODE
		if tree == LEAF:
			return self.generate_leaf()
		else:
			assert is_iterable(tree)
			op, children = tree[0], tree[1:]
			if op == UNARY:
				op = self.generate_unary()
			elif op == BINARY:
				op = self.generate_binary()
			else:
				assert op == ROOT, op
				op = self.generate_root()
			children = tuple(self.populate_tree(child) for child in children)
			return op + children

	def __call__(self, tree: Tree) -> CE:
		return self.populate_tree(tree)
