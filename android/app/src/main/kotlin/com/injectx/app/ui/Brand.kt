package com.injectx.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import com.injectx.app.ui.theme.Accent
import com.injectx.app.ui.theme.BadRed
import com.injectx.app.ui.theme.InfoBlue
import com.injectx.app.ui.theme.OkGreen
import com.injectx.app.ui.theme.TextLo
import com.injectx.app.ui.theme.TextMid
import com.injectx.app.ui.theme.WarnAmber
import kotlin.math.cos
import kotlin.math.sin

/** Flat hexagon + "X" mark — a single tone, no glow. A quiet brand glyph. */
@Composable
fun HexLogo(modifier: Modifier = Modifier, color: Color = Accent) {
    Canvas(modifier) {
        val w = size.minDimension
        val cx = size.width / 2f
        val cy = size.height / 2f
        val r = w * 0.46f

        val hex = Path()
        for (i in 0..5) {
            val a = Math.toRadians((60.0 * i - 90.0))
            val px = cx + r * cos(a).toFloat()
            val py = cy + r * sin(a).toFloat()
            if (i == 0) hex.moveTo(px, py) else hex.lineTo(px, py)
        }
        hex.close()
        drawPath(hex, color, style = Stroke(width = w * 0.05f))

        val xr = r * 0.46f
        drawLine(color, Offset(cx - xr, cy - xr), Offset(cx + xr, cy + xr), strokeWidth = w * 0.06f, cap = StrokeCap.Round)
        drawLine(color, Offset(cx + xr, cy - xr), Offset(cx - xr, cy + xr), strokeWidth = w * 0.06f, cap = StrokeCap.Round)
    }
}

/** Format tags are neutral — only status carries colour (calm hierarchy). */
fun formatColor(format: String?): Color = TextMid

/** Muted status tone for a decryption_status. */
fun statusColor(status: String?): Color = when (status?.lowercase()) {
    "success" -> OkGreen
    "partial" -> WarnAmber
    "failed" -> BadRed
    "not_encrypted" -> InfoBlue
    else -> TextLo
}
