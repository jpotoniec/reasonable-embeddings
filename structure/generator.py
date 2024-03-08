import lzma
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Callable

import dill
import numpy as np
from tqdm import trange, tqdm

from HermiTWrapper import HermitReasoner
from src.generate import REASONER_TIMEOUT
from src.generators import AxiomGeneratorRL
from src.generators.UniformMaxHeightTreeGenerator import UniformMaxHeightTreeGenerator, populate_onto
from src.simplefact import Onto, Reasoner, Axiom
from src.simplefact.syntax import SUB, ANY, TOP


@dataclass
class KBHiperparameters:
	n_atomic: int
	n_roles: int
	n_axioms: int
	p_atomic: float


class DataGenerator:
	def __init__(self, rng: np.random.Generator):
		self.rng = rng
		self.max_failures = 100

	def generate_kb(self, hp: KBHiperparameters, depth: int) -> Onto:
		gen = UniformMaxHeightTreeGenerator(depth)
		for _ in trange(self.max_failures, position=1, desc="FAIL"):
			forest = [gen.generate(self.rng) for _ in range(hp.n_axioms)]
			axiom_generator = AxiomGeneratorRL(rng=self.rng, n_atomic=hp.n_atomic, p_atomic=hp.p_atomic,
											   n_roles=hp.n_roles)
			onto = Onto(tbox=set(), n_concepts=axiom_generator.n_atomic, n_roles=axiom_generator.n_roles)
			if populate_onto(onto, trees=forest, generate=axiom_generator.populate_tree):
				return onto
		raise RuntimeError("Maximum number of failures exceeded")

	def generate_queries(self, hp: KBHiperparameters, depth: int, n_queries: int) -> list[Axiom]:
		gen = UniformMaxHeightTreeGenerator(depth)
		axiom_generator = AxiomGeneratorRL(rng=self.rng, n_atomic=hp.n_atomic, p_atomic=hp.p_atomic, n_roles=hp.n_roles)
		queries = set()
		while len(queries) < n_queries:
			tree = gen.generate(self.rng)
			query = axiom_generator.populate_tree(tree)
			queries.add(query)
		return list(queries)

	def label_queries(self, reasoner, queries: list[Axiom]) -> list[bool]:
		answers = []
		for query in tqdm(queries, position=3, desc="QL"):
			try:
				answers.append(reasoner.check_axiom(query))
			except:
				print(query)
				raise
		return answers


def generate_dataset(*, rng: np.random.Generator, n_onto: int, n_queries: int, min_depth: int, max_depth: int,
					 get_n_atomic: Callable[[], int], get_n_roles: Callable[[], int], get_n_axioms: Callable[[], int],
					 get_p_atomic: Callable[[], float]):
	hiperparameters = [
		KBHiperparameters(get_n_atomic(), get_n_roles(), get_n_axioms(), get_p_atomic())
		for _ in range(n_onto)
	]

	dg = DataGenerator(rng)

	results = []

	for hp in tqdm(hiperparameters, position=0, desc="HP"):
		kbs = {}
		for depth in trange(min_depth, max_depth + 1, position=1, desc="KB"):
			kbs[depth] = dg.generate_kb(hp, depth)
		queries = {depth: dg.generate_queries(hp, depth, n_queries) for depth in
				   trange(min_depth, max_depth + 1, position=1, desc="Q ")}
		labels = {}
		if n_queries > 0:
			for kb_depth in trange(min_depth, max_depth + 1, position=1, desc="L1"):
				with HermitReasoner(kbs[kb_depth]) as reasoner:
					for queries_depth in trange(min_depth, max_depth + 1, position=2, desc="L2"):
						labels[(kb_depth, queries_depth)] = dg.label_queries(reasoner, queries[queries_depth])
		results.append((kbs, queries, labels))

	return [hiperparameters, results]


def main():
	rng = np.random.default_rng(2024)
	dataset = generate_dataset(
		rng=rng,
		n_onto=60,
		n_queries=2000,
		min_depth=2,
		max_depth=8,
		get_n_atomic=lambda: int(rng.integers(80, 120 + 1)),
		get_n_roles=lambda: int(rng.integers(1, 5 + 1)),
		get_n_axioms=lambda: int(rng.normal(200, 10)),
		get_p_atomic=lambda: float(rng.uniform(.9, 1))
	)

	output_dir = Path(__file__).parent.parent / 'local/out/structure'
	output_dir.mkdir(parents=True, exist_ok=True)
	with lzma.open(output_dir / 'dataset.dill.xz', 'wb') as f:
		dill.dump(dataset, file=f)


if __name__ == '__main__':
	main()
