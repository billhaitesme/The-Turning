package arc.omega.bridgezero

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Native mapping of bridge/shared/mobile/design-tokens.json. */
object BridgeDesign {
    object Colors {
        val Void = Color(0xFF071016)
        val Panel = Color(0xFF0E171D)
        val Raised = Color(0xFF15232B)
        val Signal = Color(0xFF38D1E8)
        val Nominal = Color(0xFF57D492)
        val Warning = Color(0xFFF2AD40)
        val Failure = Color(0xFFF05252)
        val Separator = Color(0xFF24333C)
    }

    object Spacing {
        val Xs = 4.dp
        val Sm = 8.dp
        val Md = 12.dp
        val Lg = 16.dp
        val Xl = 24.dp
    }

    object Radius {
        val Badge = 6.dp
        val Control = 8.dp
        val Card = 12.dp
    }

    /**
     * Typography tokens mirroring the shared `typography` map. Compose expresses letter
     * spacing as a TextUnit, so the shared point-based `tracking` values are mapped to sp
     * (the natural per-platform unit); iOS applies the same numbers as point tracking. This
     * unit mapping is the one intentional platform-specific difference in typography.
     */
    object Type {
        val Display = TextStyle(fontSize = 34.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
        val Title = TextStyle(fontSize = 22.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
        val Body = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Normal, letterSpacing = 0.sp)
        val Label = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.4.sp)
        val Metric = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Normal, fontFamily = FontFamily.Monospace)
    }

    /** Shared semantic status -> color map (design-tokens.json `status`). */
    fun statusColor(state: String): Color = when (state.lowercase()) {
        "online", "healthy" -> Colors.Nominal
        "streaming" -> Colors.Signal
        "degraded", "locked" -> Colors.Warning
        "offline" -> Colors.Failure
        "unavailable" -> Colors.Separator
        else -> Colors.Separator
    }
}

/**
 * Reusable status badge matching the iOS `StatusBadge`: an uppercased monospace label tinted
 * by the semantic status color, on a 12%-opacity fill with a 35%-opacity outline at badge
 * radius. Closes the prior Android gap where no shared badge component existed.
 */
@Composable
fun StatusBadge(label: String, color: Color) {
    Text(
        text = label.uppercase(),
        color = color,
        style = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace),
        modifier = Modifier
            .background(color.copy(alpha = 0.12f), RoundedCornerShape(BridgeDesign.Radius.Badge))
            .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(BridgeDesign.Radius.Badge))
            .padding(horizontal = BridgeDesign.Spacing.Sm, vertical = BridgeDesign.Spacing.Xs),
    )
}
