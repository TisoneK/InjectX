package com.injectx.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import com.injectx.app.ui.theme.Amber
import com.injectx.app.ui.theme.Cyan
import com.injectx.app.ui.theme.NeonGreen
import com.injectx.app.ui.theme.Red
import com.injectx.app.ui.theme.TextLo
import kotlin.math.cos
import kotlin.math.sin

/** Crisp, glowing hexagon + "X" mark drawn with Canvas (matches the app icon). */
@Composable
fun HexLogo(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val w = size.minDimension
        val cx = size.width / 2f
        val cy = size.height / 2f
        val r = w * 0.44f

        val hex = Path()
        for (i in 0..5) {
            val a = Math.toRadians((60.0 * i - 90.0))
            val px = cx + r * cos(a).toFloat()
            val py = cy + r * sin(a).toFloat()
            if (i == 0) hex.moveTo(px, py) else hex.lineTo(px, py)
        }
        hex.close()
        // hexagon glow → crisp
        drawPath(hex, Cyan.copy(alpha = 0.08f), style = Stroke(width = w * 0.11f))
        drawPath(hex, Cyan.copy(alpha = 0.16f), style = Stroke(width = w * 0.06f))
        drawPath(hex, Cyan, style = Stroke(width = w * 0.022f))

        // the X
        val xr = r * 0.5f
        val tl = Offset(cx - xr, cy - xr); val br = Offset(cx + xr, cy + xr)
        val tr = Offset(cx + xr, cy - xr); val bl = Offset(cx - xr, cy + xr)
        fun x(color: Color, width: Float) {
            drawLine(color, tl, br, strokeWidth = width, cap = StrokeCap.Round)
            drawLine(color, tr, bl, strokeWidth = width, cap = StrokeCap.Round)
        }
        x(NeonGreen.copy(alpha = 0.10f), w * 0.16f)
        x(NeonGreen.copy(alpha = 0.22f), w * 0.10f)
        x(NeonGreen, w * 0.055f)
    }
}

/** A distinct accent per config format. */
fun formatColor(format: String?): Color = when (format?.lowercase()) {
    "ehi" -> Cyan
    "hc" -> NeonGreen
    "ziv" -> Amber
    "dark", "darktunnel" -> Color(0xFF9B7BFF)
    "tls" -> Red
    "npv", "nsh", "vhd", "hat" -> Color(0xFF6EC1FF)
    else -> TextLo
}

/** Status pill colour for a decryption_status. */
fun statusColor(status: String?): Color = when (status?.lowercase()) {
    "success" -> NeonGreen
    "partial" -> Amber
    "failed" -> Red
    "not_encrypted" -> Cyan
    else -> TextLo
}
