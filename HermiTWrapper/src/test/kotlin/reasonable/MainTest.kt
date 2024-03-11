package  reasonable

import reasonable.JsonToOWL.Companion.DIS
import reasonable.JsonToOWL.Companion.SUB
import reasonable.JsonToOWL.Companion.TOP
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class MainTest {

    @Test
    fun test_add_remove() {
        val main = Main(null)
        assertTrue { main.process("add", "[$DIS, 1, 2]").toBoolean() }
        assertTrue { main.process("add", "[$SUB, $TOP, 1]").toBoolean() }
        assertFalse { main.process("add", "[$SUB, $TOP, 2]").toBoolean() }
        assertTrue { main.process("remove", "[$DIS, 1, 2]").toBoolean() }
    }

    @Test
    fun test_add_remove_last() {
        val main = Main(null)
        assertTrue { main.process("add", "[$DIS, 1, 2]").toBoolean() }
        assertTrue { main.process("add", "[$SUB, $TOP, 1]").toBoolean() }
        assertFalse { main.process("add", "[$SUB, $TOP, 2]").toBoolean() }
        assertTrue { main.process("remove", "").toBoolean() }
        assertEquals(2, main.ontology.axiomCount)
    }

    @Test
    fun test_is_entailed() {
        val main = Main(null)
        assertTrue { main.process("add", "[$SUB, 1, 2]").toBoolean() }
        assertTrue { main.process("add", "[$SUB, 2, 3]").toBoolean() }
        assertTrue { main.process("isEntailed", "[$SUB, 1, 3]").toBoolean() }
        assertFalse { main.process("isEntailed", "[$SUB, 3, 1]").toBoolean() }
    }
}
