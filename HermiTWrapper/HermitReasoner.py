import subprocess
import sys
import tempfile

from pathlib import Path

from src.simplefact import Onto, Axiom
from . import rdf


class HermitReasoner:
	def __init__(self, kb: Onto):
		self.kb = kb
		self.file = Path(tempfile.mktemp())

	def __enter__(self):
		jar = Path(__file__).parent / 'target/HermiTWrapper-1.0-SNAPSHOT.jar'
		assert jar.exists(), "Go to HermiTWrapper and run mvn package"
		rdf.to_rdf(self.kb).serialize(self.file, format='xml')
		cmd = ['java', '-jar', jar, self.file]
		self.hermit = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr)
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.hermit.kill()
		self.hermit.wait()
		self.file.unlink()

	def check_axiom(self, query: Axiom):
		tmp = Onto(tbox={query}, n_concepts=self.kb.n_concepts, n_roles=self.kb.n_roles)
		rdf.to_rdf(tmp).serialize(self.hermit.stdin, format="xml")
		self.hermit.stdin.write(b'\n')
		self.hermit.stdin.flush()
		text = self.hermit.stdout.readline().decode().strip()
		return text == 'true'
