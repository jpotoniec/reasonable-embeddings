package reasonable

import kotlinx.serialization.json.*
import org.semanticweb.HermiT.Configuration
import org.semanticweb.HermiT.EntailmentChecker
import org.semanticweb.HermiT.Reasoner
import org.semanticweb.owlapi.apibinding.OWLManager
import org.semanticweb.owlapi.model.*
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader


class JsonToOWL(val dataFactory: OWLDataFactory) {

    companion object {
        const val TOP = -1
        const val BOT = -2
        const val SUB = 0
        const val EQV = 1
        const val DIS = 2
        const val NOT = 3
        const val AND = 4
        const val OR = 5
        const val ALL = 6
        const val ANY = 7
    }

    fun toClass(element: JsonPrimitive): OWLClass =
        when (element.int) {
            TOP -> dataFactory.owlThing
            BOT -> dataFactory.owlNothing
            else -> dataFactory.getOWLClass(IRI.create("http://example.com/foo#C${element.int}"))
        }

    fun toObjectProperty(element: JsonElement): OWLObjectProperty {
        check(element is JsonPrimitive)
        return dataFactory.getOWLObjectProperty(IRI.create("http://example.com/foo#R${element.int}"))
    }

    fun toClassExpression(element: JsonElement): OWLClassExpression {
        if (element is JsonPrimitive) {
            return toClass(element)
        } else {
            check(element is JsonArray)
            check(element.size in 2..3)
            val op = element[0]
            check(op is JsonPrimitive)
            return when (op.int) {
                NOT -> dataFactory.getOWLObjectComplementOf(toClassExpression(element[1]))
                AND -> dataFactory.getOWLObjectIntersectionOf(
                    toClassExpression(element[1]),
                    toClassExpression(element[2])
                )

                OR -> dataFactory.getOWLObjectUnionOf(toClassExpression(element[1]), toClassExpression(element[2]))
                ALL -> dataFactory.getOWLObjectAllValuesFrom(
                    toObjectProperty(element[1]),
                    toClassExpression(element[2])
                )

                ANY -> dataFactory.getOWLObjectSomeValuesFrom(
                    toObjectProperty(element[1]),
                    toClassExpression(element[2])
                )

                else -> error("Unexpected operator ${op.int}")
            }
        }
    }

    fun toAxiom(element: JsonElement): OWLAxiom {
        check(element is JsonArray)
        check(3 == element.size)
        val op = element[0]
        check(op is JsonPrimitive)
        check(op.int in setOf(SUB, EQV, DIS))
        val left = toClassExpression(element[1])
        val right = toClassExpression(element[2])
        return when (op.int) {
            SUB -> dataFactory.getOWLSubClassOfAxiom(left, right)
            DIS -> dataFactory.getOWLSubClassOfAxiom(
                dataFactory.getOWLObjectIntersectionOf(left, right),
                dataFactory.owlNothing
            )

            EQV -> dataFactory.getOWLEquivalentClassesAxiom(left, right)
            else -> error("Unexpected operator ${op.int}")
        }
    }

    fun toAxiom(json: String) = toAxiom(Json.parseToJsonElement(json))
}

class Main(ontologyFile: String?) {

    val m = OWLManager.createOWLOntologyManager()
    val jsonToOWL = JsonToOWL(m.owlDataFactory)
    private var lastAxiom: OWLAxiom? = null

    val ontology = if (ontologyFile !== null)
        m.loadOntology(IRI.create(File(ontologyFile)))
    else
        m.createOntology()
    val hermit = Reasoner(Configuration(), ontology)

    fun add(json: String): String {
        val axiom = jsonToOWL.toAxiom(json)
        m.applyChanges(m.addAxiom(ontology, axiom))
        lastAxiom = axiom
        hermit.flush()
        return hermit.isConsistent.toString()
    }

    fun remove(json: String): String {
        val axiom = if (json.isEmpty()) checkNotNull(lastAxiom) else jsonToOWL.toAxiom(json)
        m.applyChanges(m.removeAxiom(ontology, axiom))
        hermit.flush()
        return hermit.isConsistent.toString()
    }

    fun isEntailed(json: String): String {
        val checker = EntailmentChecker(hermit, m.owlDataFactory)
        val isEntailed = checker.entails(jsonToOWL.toAxiom(json))
        return isEntailed.toString()
    }

    fun process(command: String, json: String): String =
        when (command) {
            "add" -> add(json)
            "remove" -> remove(json)
            "isEntailed" -> isEntailed(json)
            else -> error("Unknown command `$command'")
        }

    companion object {
        @JvmStatic
        fun main(args: Array<String>): Unit {
            val processor = Main(if (args.isNotEmpty()) args[0] else null)
            val reader = BufferedReader(InputStreamReader(System.`in`))
            while (true) {
                val command = reader.readLine()?.trim() ?: break
                if (command.isEmpty())
                    break
                val json = reader.readLine().trim()
                println(processor.process(command, json))
            }
        }
    }
}
