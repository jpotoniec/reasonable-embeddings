from src.simplefact import Onto
from src.simplefact.syntax import SUB, TOP, DIS
from .HermitReasoner import HermitReasoner


def test_add_remove_axioms():
	with HermitReasoner() as reasoner:
		reasoner.add_axiom((DIS, 1, 2))
		assert reasoner.is_consistent()
		reasoner.add_axiom((SUB, TOP, 1))
		assert reasoner.is_consistent()
		reasoner.add_axiom((SUB, TOP, 2))
		assert not reasoner.is_consistent()
		reasoner.retract_last()
		assert reasoner.is_consistent()


def test_trivial_inference():
	kb = Onto(tbox=set(), n_concepts=10, n_roles=5)
	kb.tbox.add((SUB, 1, 2))
	kb.tbox.add((SUB, 2, 3))
	with HermitReasoner(kb) as reasoner:
		assert reasoner.check_axiom((SUB, 1, 3))


def test_negative_inference():
	kb = Onto(tbox=set(), n_concepts=10, n_roles=5)
	kb.tbox.add((SUB, 1, 2))
	kb.tbox.add((SUB, 2, 3))
	with HermitReasoner(kb) as reasoner:
		assert not reasoner.check_axiom((SUB, 3, 1))


def test_consecutive_negative_inference():
	"""To make sure checked axiom is not asserted"""
	kb = Onto(tbox=set(), n_concepts=10, n_roles=5)
	kb.tbox.add((SUB, 1, 2))
	kb.tbox.add((SUB, 2, 3))
	with HermitReasoner(kb) as reasoner:
		assert not reasoner.check_axiom((SUB, 3, 1))
		assert not reasoner.check_axiom((SUB, 3, 1))
