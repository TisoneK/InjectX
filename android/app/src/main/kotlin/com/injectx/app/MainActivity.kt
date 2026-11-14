package com.injectx.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * App shell only — Phase 6 (UI) fills this in: Storage Access Framework file
 * pick -> [com.injectx.core] detect/decrypt -> show the normalized config +
 * audit trace. Right now it renders a placeholder so the module has an entry
 * point; no logic lives in `app` (it all lives in the testable `:core`).
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                Column(Modifier.padding(24.dp)) {
                    Text("InjectX", style = MaterialTheme.typography.headlineMedium)
                    Text("VPN config reader — UI pending (Phase 6).")
                }
            }
        }
    }
}
