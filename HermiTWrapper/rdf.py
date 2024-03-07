from typing import Sequence

import rdflib
from rdflib import RDFS, OWL, RDF, BNode, IdentifiedNode

from src.simplefact import Onto
from src.simplefact.syntax import SUB, DIS, TOP, BOT, AND, OR, EXISTS, ALL, NOT


def is_iterable(item):
	try:
		iter(item)
		return True
	except TypeError:
		return False


class ToRDF:
	def __init__(self):
		self.graph = rdflib.Graph(base='http://example.com/foo#')
		self.ns = rdflib.Namespace(self.graph.base)
		self.known_classes = set()
		self.known_roles = set()

	def concept(self, c: int):
		iri = self.ns[f"C{c}"]
		if c not in self.known_classes:
			self.graph.add((iri, RDF['type'], OWL['Class']))
		return iri

	def role(self, r: int):
		iri = self.ns[f"R{r}"]
		if r not in self.known_roles:
			self.graph.add((iri, RDF['type'], OWL['ObjectProperty']))
		return iri

	def convert(self, onto: Onto):
		for axiom in onto.tbox:
			self.add_axiom(axiom)

	def _to_list(self, items: Sequence[IdentifiedNode]) -> IdentifiedNode:
		if len(items) == 0:
			return RDF['nil']
		else:
			root = BNode()
			self.graph.add((root, RDF['type'], RDF['List']))
			self.graph.add((root, RDF['first'], items[0]))
			self.graph.add((root, RDF['rest'], self._to_list(items[1:])))
			return root

	def _to_ce(self, ce) -> IdentifiedNode:
		if is_iterable(ce):
			bnode = BNode()
			if ce[0] == AND:
				self.graph.add((bnode, RDF['type'], OWL['Class']))
				self.graph.add((bnode, OWL['intersectionOf'], self._to_list([self._to_ce(item) for item in ce[1:]])))
			elif ce[0] == OR:
				self.graph.add((bnode, RDF['type'], OWL['Class']))
				self.graph.add((bnode, OWL['unionOf'], self._to_list([self._to_ce(item) for item in ce[1:]])))
			elif ce[0] == NOT:
				self.graph.add((bnode, RDF['type'], OWL['Class']))
				self.graph.add((bnode, OWL['complementOf'], self._to_ce(ce[1])))
			elif ce[0] == EXISTS:
				self.graph.add((bnode, RDF['type'], OWL['Restriction']))
				self.graph.add((bnode, OWL['onProperty'], self.role(ce[1])))
				self.graph.add((bnode, OWL['someValuesFrom'], self._to_ce(ce[2])))
			elif ce[0] == ALL:
				self.graph.add((bnode, RDF['type'], OWL['Restriction']))
				self.graph.add((bnode, OWL['onProperty'], self.role(ce[1])))
				self.graph.add((bnode, OWL['allValuesFrom'], self._to_ce(ce[2])))
			else:
				assert False
			return bnode
		else:
			if ce == TOP:
				return OWL['Thing']
			elif ce == BOT:
				return OWL['Nothing']
			else:
				return self.concept(ce)

	def add_axiom(self, axiom):
		op = RDFS['subClassOf']
		if axiom[0] == SUB:
			left = self._to_ce(axiom[1])
			right = self._to_ce(axiom[2])
		else:
			assert axiom[0] == DIS
			left = self._to_ce((AND, axiom[1], axiom[2]))
			right = self._to_ce(BOT)
		self.graph.add((left, op, right))


def to_rdf(onto: Onto) -> rdflib.Graph:
	tordf = ToRDF()
	tordf.convert(onto)
	return tordf.graph


def main():
	tordf = ToRDF()
	# axiom = axiom_generator.populate_tree(gen.generate(rng))
	# g = rdflib.Graph(base='http://example.com/foo#')
	tordf.add_axiom((DIS, (AND, 1, 2), (OR, (EXISTS, 1, (NOT, 5)), (ALL, 2, (NOT, (OR, 6, 7))))))
	print(*tordf.graph, sep='\n')
	tordf.graph.serialize("/tmp/a.ttl")


if __name__ == '__main__':
	main()
