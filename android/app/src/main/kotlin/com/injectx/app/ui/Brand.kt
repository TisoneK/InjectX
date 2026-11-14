package com.injectx.app.ui

import androidx.compose.foundation.Image
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import com.injectx.app.R
import com.injectx.app.ui.theme.Accent
import com.injectx.app.ui.theme.BadRed
import com.injectx.app.ui.theme.Cyan
import com.injectx.app.ui.theme.TextLo
import com.injectx.app.ui.theme.WarnAmber

/**
 * The brand mark — the REAL app icon (`res/drawable/injectx_logo.png`), the one
 * single source for every placement (header, cards, empty states). Never a
 * redraw; scale this same asset. (Named HexLogo for call-site compatibility.)
 */
@Composable
fun HexLogo(modifier: Modifier = Modifier) {
    Image(
        painter = painterResource(R.drawable.injectx_logo),
        contentDescription = "InjectX",
        modifier = modifier,
    )
}

/** Color-coded per format, so the supported list is scannable at a glance. */
fun formatColor(format: String?): Color = when (format?.lowercase()) {
    "ehi" -> Cyan
    "hc" -> Accent
    "ziv" -> WarnAmber
    "dark", "darktunnel" -> Color(0xFF9B7BFF)
    "tls" -> BadRed
    "npv" -> Color(0xFF6EC1FF)
    "nsh" -> Color(0xFF7FE0C0)
    "vhd" -> Color(0xFFE08AC0)
    "hat" -> Color(0xFFC0D86E)
    else -> TextLo
}

/** Muted-but-lit status tone for a decryption_status. */
fun statusColor(status: String?): Color = when (status?.lowercase()) {
    "success" -> Accent
    "partial" -> WarnAmber
    "failed" -> BadRed
    "not_encrypted" -> Cyan
    else -> TextLo
}
