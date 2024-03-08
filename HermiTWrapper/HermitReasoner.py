import json
import subprocess
import sys

from pathlib import Path
from typing import Optional

from src.simplefact import Onto, Axiom, CE
from src.simplefact.syntax import SUB


class HermitReasoner:
	def __init__(self, kb: Optional[Onto] = None):
		self._is_consistent = True
		self.kb = kb

	def __enter__(self):
		jar = Path(__file__).parent / 'target/HermiTWrapper-1.0-SNAPSHOT.jar'
		assert jar.exists(), "Go to HermiTWrapper and run mvn package"
		cmd = ['java', '-jar', jar]
		self.hermit = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr)
		if self.kb is not None:
			for axiom in self.kb.tbox:
				self.add_axiom(axiom)
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.hermit.kill()
		self.hermit.wait()

	def add_axiom(self, axiom):
		self.hermit.stdin.write(b'add\n' + json.dumps(axiom).encode() + b'\n')
		self.hermit.stdin.flush()
		self._is_consistent = self.hermit.stdout.readline().decode().strip() == "true"

	def retract_last(self):
		self.hermit.stdin.write(b'remove\n\n')
		self.hermit.stdin.flush()
		self._is_consistent = self.hermit.stdout.readline().decode().strip() == "true"

	def is_consistent(self):
		return self._is_consistent

	def check_axiom(self, query: Axiom) -> bool:
		self.hermit.stdin.write(b'isEntailed\n' + json.dumps(query).encode() + b'\n')
		self.hermit.stdin.flush()
		return self.hermit.stdout.readline().decode().strip() == "true"

	def check_sub(self, left: CE, right: CE) -> bool:
		return self.check_axiom((SUB, left, right))
