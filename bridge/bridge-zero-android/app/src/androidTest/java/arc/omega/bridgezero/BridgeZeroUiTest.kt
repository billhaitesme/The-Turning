package arc.omega.bridgezero

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import org.junit.Rule
import org.junit.Test

class BridgeZeroUiTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test fun loginPresentsOperatorConsoleIdentity() {
        composeRule.onNodeWithText("BRIDGE ZERO").assertIsDisplayed()
        composeRule.onNodeWithText("Server Address").assertIsDisplayed()
        composeRule.onNodeWithText("Authentication Token").assertIsDisplayed()
        composeRule.onNodeWithText("CONNECT", substring = true).assertIsDisplayed()
    }
}
