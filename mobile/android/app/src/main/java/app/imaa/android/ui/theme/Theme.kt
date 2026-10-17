package app.imaa.android.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

val BrandViolet = Color(0xFF7C5CFF)
val BrandTeal = Color(0xFF00C9A7)

private val Light = lightColorScheme(
    primary = Color(0xFF6A4DF5),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFECE8FF),
    onPrimaryContainer = Color(0xFF22125F),
    secondary = Color(0xFF00B39A),
    onSecondary = Color.White,
    background = Color(0xFFF5F6FA),
    onBackground = Color(0xFF161A26),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF161A26),
    surfaceVariant = Color(0xFFF0F1F7),
    onSurfaceVariant = Color(0xFF5F6678),
    outline = Color(0xFFE3E5EE),
    error = Color(0xFFE02D3C),
)

private val Dark = darkColorScheme(
    primary = Color(0xFF8B74FF),
    onPrimary = Color.White,
    primaryContainer = Color(0xFF2A2550),
    onPrimaryContainer = Color(0xFFE6E0FF),
    secondary = Color(0xFF2ED3B7),
    onSecondary = Color(0xFF00201A),
    background = Color(0xFF0E1016),
    onBackground = Color(0xFFECEEF5),
    surface = Color(0xFF181B26),
    onSurface = Color(0xFFECEEF5),
    surfaceVariant = Color(0xFF222636),
    onSurfaceVariant = Color(0xFF9AA2B5),
    outline = Color(0xFF2A2F3E),
    error = Color(0xFFF87171),
)

@Composable
fun ImaaTheme(theme: String, content: @Composable () -> Unit) {
    val dark = when (theme) {
        "dark" -> true
        "light" -> false
        else -> isSystemInDarkTheme()
    }
    MaterialTheme(
        colorScheme = if (dark) Dark else Light,
        shapes = Shapes(
            small = RoundedCornerShape(10.dp),
            medium = RoundedCornerShape(16.dp),
            large = RoundedCornerShape(24.dp),
        ),
        content = content,
    )
}
