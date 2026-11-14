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
    primary = NeonGreen,
    onPrimary = Ink,
    primaryContainer = NeonGreenDim,
    onPrimaryContainer = TextHi,
    secondary = Cyan,
    onSecondary = Ink,
    background = Ink,
    onBackground = TextHi,
    surface = Surface1,
    onSurface = TextHi,
    surfaceVariant = Surface2,
    onSurfaceVariant = TextLo,
    outline = Outline,
    error = Red,
    onError = Ink,
)

private val InjectXShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(20.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

private val base = Typography()
private val InjectXType = base.copy(
    headlineMedium = base.headlineMedium.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
    titleLarge = base.titleLarge.copy(fontWeight = FontWeight.SemiBold),
    titleMedium = base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
    labelLarge = base.labelLarge.copy(letterSpacing = 0.5.sp),
    labelMedium = base.labelMedium.copy(color = TextLo, letterSpacing = 0.4.sp),
)

/** Monospace style for config values / code — the "terminal" feel. */
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
