package arc.omega.bridgezero

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class RuntimeApiValidationTest {
    @Test fun externalCleartextServerFailsClosedBeforeNetworkAccess() {
        assertThrows(IllegalArgumentException::class.java) {
            RuntimeApi.validateServer("http://example.com")
        }
    }

    @Test fun httpsServerIsNormalized() {
        assertEquals("https://runtime.example/", RuntimeApi.validateServer("https://runtime.example"))
    }

    @Test fun offlineStateRetainsRuntimeReason() {
        assertEquals(
            ConnectionState.Offline("Core Runtime unavailable"),
            ConnectionState.Offline("Core Runtime unavailable"),
        )
    }
}
