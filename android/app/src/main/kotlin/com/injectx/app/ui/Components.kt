package com.injectx.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.injectx.app.ui.theme.Accent
import com.injectx.app.ui.theme.BadRed
import com.injectx.app.ui.theme.InfoBlue
import com.injectx.app.ui.theme.OkGreen
import com.injectx.app.ui.theme.Outline
import com.injectx.app.ui.theme.Surface1
import com.injectx.app.ui.theme.Surface2
import com.injectx.app.ui.theme.TextLo
import com.injectx.app.ui.theme.WarnAmber

/** A quiet tag — subtle surface, no glow or coloured outline; colour lives in the text only. */
@Composable
internal fun Pill(text: String, color: Color) {
    Surface(color = Surface2, shape = RoundedCornerShape(6.dp)) {
        Text(
            text,
            style = MaterialTheme.typography.labelMedium.copy(color = color),
            modifier = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
        )
    }
}

@Composable
internal fun SectionLabel(text: String) {
    Text(text, style = MaterialTheme.typography.labelMedium, color = TextLo)
}

/**
 * The one card surface used across the app (Home, Decode, SNI): rounded
 * Surface1 with a hairline Outline border, so every screen reads as one system.
 */
@Composable
internal fun PanelCard(
    modifier: Modifier = Modifier,
    border: Boolean = true,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    val base = modifier.fillMaxWidth().let { if (onClick != null) it.clickable { onClick() } else it }
    Surface(
        color = Surface1,
        shape = RoundedCornerShape(16.dp),
        border = if (border) BorderStroke(1.dp, Outline) else null,
        modifier = base,
    ) { Box(Modifier.padding(16.dp)) { content() } }
}

/** The tinted, rounded icon tile from the Home tool cards — reused everywhere. */
@Composable
internal fun IconTile(icon: ImageVector, tint: Color, tile: Dp = 44.dp, glyph: Dp = 24.dp) {
    Box(
        Modifier.size(tile).background(tint.copy(alpha = 0.14f), RoundedCornerShape(tile / 4)),
        contentAlignment = Alignment.Center,
    ) { Icon(icon, null, tint = tint, modifier = Modifier.size(glyph)) }
}

/** A titled panel — PanelCard with a small label header (CONNECTION, WARNINGS, …). */
@Composable
internal fun SectionCard(title: String, accent: Color = Accent, content: @Composable () -> Unit) {
    PanelCard {
        Column {
            Text(title, style = MaterialTheme.typography.labelMedium, color = accent.copy(alpha = 0.9f))
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

/** Two-segment control, quiet styling. */
@Composable
internal fun SegmentedTabs(selected: Int, labels: List<String>, modifier: Modifier = Modifier, onSelect: (Int) -> Unit) {
    Surface(color = Surface2, shape = RoundedCornerShape(10.dp), modifier = modifier) {
        Row(Modifier.padding(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            labels.forEachIndexed { i, label ->
                val on = i == selected
                Surface(
                    color = if (on) MaterialTheme.colorScheme.surface else Color.Transparent,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f).clickable { onSelect(i) },
                ) {
                    Text(
                        label,
                        style = MaterialTheme.typography.labelLarge.copy(color = if (on) MaterialTheme.colorScheme.onSurface else TextLo),
                        modifier = Modifier.padding(vertical = 9.dp),
                        textAlign = TextAlign.Center,
                    )
                }
            }
        }
    }
}

internal fun verdictColor(verdict: String?): Color = when (verdict?.lowercase()) {
    "working" -> OkGreen
    "redirect" -> InfoBlue
    "blocked" -> WarnAmber
    "dead" -> BadRed
    else -> TextLo
}
