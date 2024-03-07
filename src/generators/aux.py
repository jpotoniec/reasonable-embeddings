from typing import Union, Tuple

Tree = Union[int, Tuple[int, 'Tree'], Tuple[int, 'Tree', 'Tree']]

NODE, ROOT, BINARY, UNARY, LEAF = range(5)


def is_iterable(item):
	try:
		iter(item)
		return True
	except TypeError:
		return False
