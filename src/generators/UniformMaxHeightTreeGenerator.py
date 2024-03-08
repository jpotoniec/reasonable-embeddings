import lzma
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable

import dill
import numpy as np
from tqdm import trange, tqdm

from HermiTWrapper import HermitReasoner
from src.generate import REASONER_TIMEOUT
from src.simplefact import Onto, Reasoner, Axiom
from src.simplefact.syntax import BOT
from src.utils import check_axiom_safe
from .aux import *


class UniformMaxHeightTreeGenerator:
	"""
	Generates unary-binary trees with the specified maximal height uniformly at random
	"""

	def __init__(self, max_height: int):
		self.max_height = max_height - 1
		self.heights = [UniformMaxHeightTreeGenerator.count_trees(h) for h in range(self.max_height + 1)]

	@staticmethod
	def count_trees(max_height: int) -> int:
		if max_height == 0:
			return 0
		elif max_height == 1:
			return 1
		else:
			a = UniformMaxHeightTreeGenerator.count_trees(max_height - 1)
			return a ** 2 + a + 1

	def decode(self, i: int, h: Optional[int] = None) -> Tree:
		if h is None:
			h = self.max_height
		if i == 0 or h == 1:
			return LEAF
		d = self.heights[h - 1]
		if i <= d:
			return UNARY, self.decode(i - 1, h - 1)
		else:
			i -= d + 1
			a = i // d
			b = i % d
			return BINARY, self.decode(a, h - 1), self.decode(b, h - 1)

	def generate(self, rng: np.random.Generator):
		n = self.heights[self.max_height]
		left = self.decode(rng.integers(0, n))
		right = self.decode(rng.integers(0, n))
		return ROOT, left, right


@dataclass
class OntoHiperparameters:
	n_atomic: int
	n_roles: int
	n_axioms: int
	p_atomic: float


def populate_onto2(reasoner: Reasoner, onto: Onto, *, trees: list[Tree], generate: Callable[[Tree], Axiom],
				   max_unsat=0.1, max_consecutive_failures: int = 100) -> bool:
	# TODO perhasp reasoner should be created here?
	max_unsat = int(max_unsat * onto.n_concepts)
	i = 0
	while i < len(trees):
		axiom = generate(trees[i])
		if axiom in onto.tbox:
			continue
		reasoner.add_axiom(axiom)
		onto.tbox.add(axiom)
		i += 1
	unsatisfiable = 0
	try:
		consistent = reasoner.is_consistent()
		if consistent:
			for c in range(onto.n_concepts):
				if reasoner.check_sub(c, BOT):
					unsatisfiable += 1
					if unsatisfiable >= max_unsat:
						break
	except RuntimeError as e:
		print(e, file=sys.stderr)
		return False
	return consistent and unsatisfiable < max_unsat


def populate_onto(onto: Onto, *, trees: list[Tree], generate: Callable[[Tree], Axiom],
				  max_unsat=0.1, max_consecutive_failures: int = 100) -> bool:
	with HermitReasoner() as reasoner:
		max_unsat = int(max_unsat * onto.n_concepts)
		failures = 0
		i = 0
		while i < len(trees):
			axiom = generate(trees[i])
			if axiom in onto.tbox:
				continue
			reasoner.add_axiom(axiom)
			unsatisfiable = 0
			try:
				consistent = reasoner.is_consistent()
				if consistent:
					for c in range(onto.n_concepts):
						if reasoner.check_sub(c, BOT):
							unsatisfiable += 1
							if unsatisfiable >= max_unsat:
								break
			except RuntimeError as e:
				print(e, file=sys.stderr)
				return False

			if consistent and unsatisfiable < max_unsat:
				onto.tbox.add(axiom)
				# rdf.to_rdf(onto).serialize("/tmp/a.ttl")
				i += 1
			else:
				reasoner.retract_last()
				failures += 1
				if failures > max_consecutive_failures:
					return False
		return True


def step(rng: np.random.Generator, hp: OntoHiperparameters, depth: int, n_queries: int,
		 max_consecutive_failures: int = 100) -> Optional[Tuple[Onto, list, list]]:
	gen = UniformMaxHeightTreeGenerator(depth)
	forest = [gen.generate(rng) for _ in range(hp.n_axioms)]
	axiom_generator = AxiomGenerator(rng=rng, n_atomic=hp.n_atomic, p_atomic=hp.p_atomic,
									 n_roles=hp.n_roles)
	onto = Onto(tbox=set(), n_concepts=axiom_generator.n_atomic, n_roles=axiom_generator.n_roles)
	reasoner = Reasoner(n_concepts=onto.n_concepts, n_roles=onto.n_roles, timeout=REASONER_TIMEOUT)
	if not populate_onto(reasoner, onto, trees=forest, generate=axiom_generator.populate_tree):
		return None

	queries = []
	answers = []

	bar = tqdm(total=n_queries, position=1, desc="Queries")
	failures = 0
	while len(queries) < n_queries:
		tree = gen.generate(rng)
		query = axiom_generator.populate_tree(tree)
		if query in queries:
			continue
		answer = check_axiom_safe(reasoner, query)
		if answer is None:
			failures += 1
			if failures >= max_consecutive_failures:
				return None
			continue
		failures = 0
		queries.append(query)
		answers.append(answer)
		bar.update(1)

	return onto, queries, answers


def main():
	"""
	1. Wygeneruj hiperparametry zbiorów niezależne od głębokości
	2. Dla każdej głębokości wygeneruj KB z danym zestawem hiperparametrów
	3. Dla każdej grupy hiperparametrów i każdej głębokości wygeneruj zestaw zapytań
	4. Zaetykietuj każde zapytanie każdą KB z tej samej rodziny hiperparametrów (nie koniecznie tej samej głębokości)
	"""

	rng = np.random.default_rng(2024)

	n_onto = 6
	n_queries = 1000
	min_depth = 8
	max_depth = 8
	get_n_atomic = lambda: int(rng.integers(80, 120 + 1))
	get_n_roles = lambda: int(rng.integers(1, 5 + 1))
	get_n_axioms = lambda: int(rng.normal(100, 10))
	get_p_atomic = lambda: float(rng.uniform(.9, 1))

	hiperparameters = [
		OntoHiperparameters(get_n_atomic(), get_n_roles(), get_n_axioms(), get_p_atomic())
		for _ in range(n_onto)
	]

	# TODO każda ontologia powinna miec zapytania testowe o różnej głębokośći
	# TODO chyba trzeba kontrolować, żeby nie próbować wygenerować za dużo zapytań dla płytkich głębokości, bo może się okazać, że nie da się bez powtórzeń

	results = []
	progressbar = tqdm(total=(max_depth - min_depth + 1) * len(hiperparameters), position=0, desc="Overall")
	for depth in trange(min_depth, max_depth + 1):
		for hp in hiperparameters:
			result = None
			while result is None:
				result = step(rng, hp, depth, n_queries)
			progressbar.update(1)

			results.append(result)

	dir = Path('../../local/out/structure/')
	dir.mkdir(parents=True, exist_ok=True)
	with lzma.open(dir / 'dataset.dill.xz', mode='wb') as f:
		dill.dump(results, f)


#
# gen = WitekGen(5)
# print(gen.generate(rng))
#
# forest = [gen.generate(rng) for _ in range(50)]
# axiom_generator = AxiomGenerator(rng=rng, n_atomic=50, p_atomic=.9, n_roles=5)
#
# onto = Onto(tbox=set(), n_concepts=axiom_generator.n_atomic, n_roles=axiom_generator.n_roles)
# reasoner = Reasoner(n_concepts=onto.n_concepts, n_roles=onto.n_roles, timeout=REASONER_TIMEOUT)
# print("Populating the ontology")
# populate_onto(reasoner, onto, trees=forest, generate=axiom_generator.populate_tree)
# print(len(onto.tbox))
#
# n_queries = 10000
# queries = []
# answers = []
# progressbar = iter(trange(n_queries))
#
# while len(queries) < n_queries:
# 	tree = gen.generate(rng)
# 	query = axiom_generator.populate_tree(tree)
# 	if query in queries:
# 		continue
# 	answer = check_axiom_safe(reasoner, query)
# 	if answer is None:
# 		continue
# 	queries.append(query)
# 	answers.append(answer)
# 	next(progressbar)
# print(len([a for a in answers if a]), len([a for a in answers if not a]))


# maxh = 3
# gen = WitekGen(maxh)
# n = WitekGen.count_trees(maxh)
# for i in range(n):
# 	print(gen.decode(i))


# for maxh in range(1, 6):
# 	gen = WitekGen(maxh)
# 	n = WitekGen.count_trees(maxh)
# 	trees = {gen.decode(i) for i in range(0, n)}
# 	assert n == len(trees)


if __name__ == '__main__':
	main()
