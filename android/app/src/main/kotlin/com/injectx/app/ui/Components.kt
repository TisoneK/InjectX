package com.injectx.app.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.injectx.app.ui.theme.Amber
import com.injectx.app.ui.theme.Cyan
import com.injectx.app.ui.theme.NeonGreen
import com.injectx.app.ui.theme.Red
import com.injectx.app.ui.theme.Surface2
import com.injectx.app.ui.theme.TextHi
import com.injectx.app.ui.theme.TextLo

@Composable
internal fun Pill(text: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.14f),
        contentColor = color,
        shape = RoundedCornerShape(8.dp),
        border = BorderStroke(1.dp, color.copy(alpha = 0.5f)),
    ) {
        Text(
            text,
            style = MaterialTheme.typography.labelMedium.copy(color = color),
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
        )
    }
}

@Composable
internal fun SectionCard(title: String, accent: Color = MaterialTheme.colorScheme.primary, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.labelMedium.copy(color = accent, letterSpacing = 1.5.sp))
            Spacer(Modifier.height(10.dp))
            content()
        }
    }
}

/** A custom segmented control (two or more segments) — on-brand, no icon deps. */
@Composable
internal fun SegmentedTabs(selected: Int, labels: List<String>, modifier: Modifier = Modifier, onSelect: (Int) -> Unit) {
    Surface(color = Surface2, shape = RoundedCornerShape(12.dp), modifier = modifier) {
        Row(Modifier.padding(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            labels.forEachIndexed { i, label ->
                val on = i == selected
                Surface(
                    color = if (on) NeonGreen.copy(alpha = 0.16f) else Color.Transparent,
                    contentColor = if (on) NeonGreen else TextLo,
                    shape = RoundedCornerShape(9.dp),
                    modifier = Modifier.weight(1f).clickable { onSelect(i) },
                ) {
                    Text(
                        label,
                        style = MaterialTheme.typography.labelLarge.copy(color = if (on) NeonGreen else TextLo),
                        modifier = Modifier.padding(vertical = 9.dp),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                    )
                }
            }
        }
    }
}

/** SNI verdict colour. */
internal fun verdictColor(verdict: String?): Color = when (verdict?.lowercase()) {
    "working" -> NeonGreen
    "redirect" -> Cyan
    "blocked" -> Amber
    "dead" -> Red
    else -> TextLo
}

internal val BrandTextHi = TextHi
