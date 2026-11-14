package com.injectx.app.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val InjectXColors = darkColorScheme(
    primary = Accent,
    onPrimary = Bg,
    primaryContainer = AccentDim,
    onPrimaryContainer = TextHi,
    secondary = InfoBlue,
    onSecondary = Bg,
    background = Bg,
    onBackground = TextHi,
    surface = Surface1,
    onSurface = TextHi,
    surfaceVariant = Surface2,
    onSurfaceVariant = TextLo,
    outline = Outline,
    outlineVariant = Divider,
    error = BadRed,
    onError = Bg,
)

private val InjectXShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(16.dp),
    extraLarge = RoundedCornerShape(24.dp),
)

// Natural, restrained type: no heavy weights, no wide tracking, sentence case.
private val base = Typography()
private val InjectXType = base.copy(
    titleLarge = base.titleLarge.copy(fontWeight = FontWeight.Medium),
    titleMedium = base.titleMedium.copy(fontWeight = FontWeight.Medium),
    bodyMedium = base.bodyMedium.copy(color = TextMid),
    labelMedium = base.labelMedium.copy(color = TextLo),
)

/** Monospace style for config values / code. */
val MonoValue = TextStyle(fontFamily = FontFamily.Monospace, fontSize = 13.sp, color = TextHi)

@Composable
fun InjectXTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = InjectXColors,
        shapes = InjectXShapes,
        typography = InjectXType,
        content = content,
    )
}
