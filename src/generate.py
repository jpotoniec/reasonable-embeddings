import os
import pickle
import json
import signal
import numpy as np
from sys import stderr
from time import time

from src.simplefact import *
from src.simplefact.syntax import *
from src.utils import *

OP_SHORT = {NOT: 'not', AND: 'and', OR: 'or', SUB: 'sub', EQV: 'eqv', ANY: 'any', ALL: 'all', BOT: 'bot', TOP: 'top', DIS: 'dis'}
OP_SHORT_INV = invdict(OP_SHORT)

REASONER_TIMEOUT = 10_000 # ms
DEFAULT_MIN_SPEED = 20 # queries per second

def AxiomGenerator(*, n_concepts, n_roles, rng, max_depth, p_atomic):
	p_top_bot = 1 - p_atomic
	def random_expr(*, max_depth):
		def gen(d):
			op = rng.choice([None, NOT, AND, OR, ANY, ALL])
			if op is None or d >= max_depth:
				return rng.choice([TOP, BOT]) if rng.random() < p_top_bot else int(rng.integers(n_concepts))
			if op == NOT:
				return op, gen(d+1)
			if op in {AND, OR}:
				return op, gen(d+1), gen(d+1)
			if op in {ALL, ANY}:
				return op, int(rng.integers(n_roles)), gen(d+1)
			assert False
		return gen(1)
	
	def random_axiom(*, max_depth=max_depth):
		max_depth = int(rng.integers(1, max_depth+1))
		op = rng.choice([SUB, DIS])
		ld = rng.integers(1, max_depth+1)
		rd = rng.integers(1, max(1, max_depth - ld)+1)
		return op, random_expr(max_depth=ld), random_expr(max_depth=rd)
		
	return random_axiom

def add_queries(reasoner, queries, answers, queries_set, answers_avg, *, n_queries, generate, min_speed, force_balance=False):
	t, i = tick(), 0
	while i < n_queries:
		if timeout(t, i, min_speed): break
		rprint(f'{fmtprog(i+1, n_queries)} extra queries (total balance {answers_avg.get():.2f})')
		axiom = generate()
		if axiom in queries_set or (answer := check_axiom_safe(reasoner, axiom)) is None:
			continue

		if force_balance and (answers_avg.get() < 0.5 and answer is False or answers_avg.get() > 0.5 and answer is True):
			continue

		queries_set.add(axiom); queries.append(axiom); answers_avg.append(answer); answers.append(answer)
		i += 1
	print()

def add_axioms(reasoner, onto, *, n_axioms, generate, max_unsat=0.1, min_speed=DEFAULT_MIN_SPEED):
	Nc = onto.n_concepts
	max_unsat = int(max_unsat*Nc)
	i, t = 0, tick()
	while i < n_axioms:
		if timeout(t, i, min_speed): break
		rprint(f'{fmtprog(i+1, n_axioms)} axioms')
		axiom = generate(max_depth=3)
		if axiom in onto.tbox:
			continue

		reasoner.add_axiom(axiom)
		consistent = reasoner.is_consistent()
		unsatisfiable = 0
		if consistent:
			for c in range(onto.n_concepts):
				if reasoner.check_sub(c, BOT):
					unsatisfiable += 1
					if unsatisfiable >= max_unsat:
						break
				
		if consistent and unsatisfiable < max_unsat:
			onto.tbox.add(axiom)
			i += 1
		else:
			reasoner.retract_last()
	print()

def gen_onto(*, rng, min_concepts, max_concepts, min_roles, max_roles, n_axioms, n_queries, min_speed=DEFAULT_MIN_SPEED, max_basic_queries=None):
	Nc = int(rng.integers(min_concepts, max_concepts+1))
	Nr = int(rng.integers(min_roles, max_roles+1))
	n_axioms = int(rng.normal(n_axioms, 10))
	p_atomic = rng.uniform(0.9, 1)
	generate = AxiomGenerator(rng=rng, n_concepts=Nc, n_roles=Nr, max_depth=3, p_atomic=p_atomic)
	reasoner = Reasoner(n_concepts=Nc, n_roles=Nr, timeout=REASONER_TIMEOUT)
	onto = Onto(tbox=set(), n_concepts=Nc, n_roles=Nr)
	add_axioms(reasoner, onto, n_axioms=n_axioms, generate=generate, min_speed=min_speed)

	X, y, X_set, y_avg = [], [], set(), RunningMean()
	add_queries(reasoner, X, y, X_set, y_avg, n_queries=n_queries, generate=generate, min_speed=min_speed)
	X, y = jointshuffle(rng, X, y)
	y = np.array(y)

	if len(X) < 3*len(onto.tbox): return None # too few queries :(
	return onto, X, y

def generate_dataset(n_ontos, *, rng, **params):
	ontos = []
	queries = []
	answers = []
	for i in range(n_ontos):
		result = None
		while result is None:
			print('---')
			print(f'{fmtprog(i+1, n_ontos)} onto')
			result = gen_onto(rng=rng, **params)
			if result is None:
				print('\nskip')
				continue
			onto, X, y = result
			ontos.append(onto)
			queries.append(X)
			answers.append(y)
			print(f'done with balance {np.mean(y):.2f}')

	return ontos, queries, answers

def generate_and_split_dataset(*, train_ontos, test_ontos, valid_size=0.2, save=None, **params):
	train_onto, train_queries, train_answers = generate_dataset(n_ontos=train_ontos, **params)
	test_onto, test_queries, test_answers = generate_dataset(n_ontos=test_ontos, **params)

	idx_tr, X_tr, y_tr = [], [], []
	idx_vl, X_vl, y_vl = [], [], []
	idx_te, X_te, y_te = [], [], []

	for onto_idx, (queries, answers) in enumerate(zip(train_queries, train_answers)):
		val_idx = int(len(queries)*(1-valid_size))
		queries, queries_vl = queries[:val_idx], queries[val_idx:]
		answers, answers_vl = answers[:val_idx], answers[val_idx:]
		for query, answer in zip(queries, answers):
			idx_tr.append(onto_idx); X_tr.append(query); y_tr.append(answer)
		for query, answer in zip(queries_vl, answers_vl):
			idx_vl.append(onto_idx); X_vl.append(query); y_vl.append(answer)

	for onto_idx, (queries, answers) in enumerate(zip(test_queries, test_answers)):
		for query, answer in zip(queries, answers):
			idx_te.append(onto_idx)
			X_te.append(query)
			y_te.append(answer)

	assert len(idx_tr) == len(X_tr) == len(y_tr)
	assert len(idx_te) == len(X_te) == len(y_te)
	assert len(idx_vl) == len(X_vl) == len(y_vl)

	result = train_onto, test_onto, (idx_tr, X_tr, y_tr), (idx_vl, X_vl, y_vl), (idx_te, X_te, y_te)
	if save: save_dataset(result, path=save)
	return result

def to_prefix(expr):
	"""
	Serializes a given expression to Polish notation.

	assert x == parse_prefix(to_prefix(x))
	"""
	if isinstance(expr, tuple):
		head = expr[0]
		op = OP_SHORT[head]
		if head in OP_UNARY:
			return op + ' ' + to_prefix(expr[1])
		elif head in OP_BINARY:
			return op + ' ' + to_prefix(expr[1]) + ' ' + to_prefix(expr[2])
		elif head in OP_QUANTIFIER:
			return op + ' ' + str(expr[1]) + ' ' + to_prefix(expr[2])
		else:
			assert False, f'unknown operator {head}'
	elif expr == BOT:
		return 'bot'
	elif expr == TOP:
		return 'top'
	else:
		return str(expr)

def parse_prefix(text):
	"""
	Parses a given expression in Polish notation.

	assert x == parse_prefix(to_prefix(x))
	"""
	def do(tokens):
		token = tokens.pop()
		if token.isnumeric():
			return int(token)

		head = OP_SHORT_INV.get(token)
		if head is None:
			assert False, f'unknown token {token} ({text})'

		if head in OP_UNARY:
			return head, do(tokens)
		elif head in OP_BINARY:
			return head, do(tokens), do(tokens)
		elif head in OP_QUANTIFIER:
			return head, int(tokens.pop()), do(tokens)
		return head

	return do(text.split(' ')[::-1])

def serialize_ontos(ontos):
	return [dict(n_concepts=onto.n_concepts, n_roles=onto.n_roles,
		tbox=[to_prefix(x) for x in onto.tbox]) for onto in ontos]

def deserialize_ontos(ontos):
	return [Onto(n_concepts=onto['n_concepts'], n_roles=onto['n_roles'],
		tbox={parse_prefix(x) for x in onto['tbox']}) for onto in ontos]

def serialize_queries(queries):
	idxs, xs, ys = queries
	return [(idx, to_prefix(x), int(y)) for idx, x, y in zip(idxs, xs, ys)]

def deserialize_queries(queries):
	return tuple(zip(*[(idx, parse_prefix(x), float(y)) for idx, x, y in queries]))

def serialize_dataset(dataset):
	train_onto, test_onto, train_queries, valid_queries, test_queries = dataset
	return dict(
		train_ontos=serialize_ontos(train_onto),
		test_ontos=serialize_ontos(test_onto),
		train_queries=serialize_queries(train_queries),
		valid_queries=serialize_queries(valid_queries),
		test_queries=serialize_queries(test_queries),
	)

def deserialize_dataset(data):
	return (deserialize_ontos(data['train_ontos']),
		deserialize_ontos(data['test_ontos']),
		deserialize_queries(data['train_queries']),
		deserialize_queries(data['valid_queries']),
		deserialize_queries(data['test_queries']),
	)

def save_dataset(dataset, *, path):
	with open(path, 'w') as f:
		json.dump(serialize_dataset(dataset), f, indent=2)

def load_dataset(path):
	if path.endswith('.pkl'):
		with open(path, 'rb') as f:
			return pickle.load(f)
	if path.endswith('.json'):
		with open(path) as f:
			return deserialize_dataset(json.load(f))
	assert False, 'Bad extension'

if __name__ == '__main__':
	seed = 42
	rng = np.random.default_rng(seed)
	generate_and_split_dataset(rng=rng, train_ontos=40, test_ontos=20,
		min_concepts=80, max_concepts=120, min_roles=1, max_roles=5, n_axioms=200, n_queries=2000,
		save='local/out/dataset/sub-40-20-new.json')
