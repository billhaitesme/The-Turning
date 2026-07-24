package arc.omega.bridgezero

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SseParserTest {
    @Test fun parsesDelta() {
        val parser = SseParser()
        assertNull(parser.consume("data: {\"type\":\"delta\",\"text\":\"Core\"}"))
        assertEquals(StreamEvent.Delta("Core"), parser.consume(""))
    }

    @Test fun preservesRuntimePhase() {
        val parser = SseParser()
        parser.consume("data: {\"type\":\"phase\",\"name\":\"guide\"}")
        assertEquals(StreamEvent.Phase("guide"), parser.consume(""))
    }
}
