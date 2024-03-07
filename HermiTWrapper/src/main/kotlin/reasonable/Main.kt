package reasonable

import org.semanticweb.HermiT.Configuration
import org.semanticweb.HermiT.EntailmentChecker
import org.semanticweb.HermiT.Reasoner
import org.semanticweb.owlapi.apibinding.OWLManager
import org.semanticweb.owlapi.model.IRI
import java.io.BufferedReader
import java.io.ByteArrayInputStream
import java.io.File
import java.io.InputStreamReader


class Main {
    companion object {
        @JvmStatic
        fun main(args: Array<String>): Unit {
            val premisePath = args[0]

            val m = OWLManager.createOWLOntologyManager()
            val ontology = m.loadOntology(IRI.create(File(premisePath)))
            val hermit = Reasoner(Configuration(), ontology)
            val reader = BufferedReader(InputStreamReader(System.`in`))
            val document = StringBuilder()
            while (true) {
                document.clear()
                while (true) {
                    val line = reader.readLine()
                    if (line == null || line.isEmpty())
                        break
                    document.append(line)
                }
                if (document.isEmpty())
                    break
                val conclusions = ByteArrayInputStream(document.toString().encodeToByteArray()).use { input ->
                    m.loadOntologyFromOntologyDocument(input)
                }
                val checker = EntailmentChecker(hermit, m.owlDataFactory)
                val isEntailed = checker.entails(conclusions.logicalAxioms)
                println(isEntailed)
            }
        }
    }
}
