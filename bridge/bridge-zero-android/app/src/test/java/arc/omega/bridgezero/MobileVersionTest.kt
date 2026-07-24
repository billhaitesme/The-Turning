package arc.omega.bridgezero

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MobileVersionTest {
    @Test fun compatibleVersionPasses() {
        assertTrue(MobileVersion.compatible(Compatibility("0.2.0", "0.2.0", "1")))
    }

    @Test fun newerRequiredVersionIsBlocked() {
        assertFalse(MobileVersion.compatible(Compatibility("0.3.0", "0.3.0", "1")))
    }

    @Test fun differentApiMajorIsBlocked() {
        assertFalse(MobileVersion.compatible(Compatibility("0.3.0", "0.2.0", "2")))
    }
}
