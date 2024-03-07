from .owlfun import *
from .factpp import Reasoner
from .syntax import expr_depth, to_pretty

CE = int | tuple[int, 'CE'] | tuple[int, 'CE', 'CE'] | tuple[int, int, 'CE']
Axiom = tuple[int, CE, CE]
