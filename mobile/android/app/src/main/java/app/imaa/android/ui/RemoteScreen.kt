package app.imaa.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import app.imaa.android.ImaaApp
import app.imaa.android.R
import app.imaa.android.core.ImaaState
import app.imaa.android.vision.GestureService

@Composable
fun RemoteScreen(modifier: Modifier) {
    val context = LocalContext.current
    val prefs = ImaaApp.prefs
    val version by prefs.version.collectAsState()
    val status by ImaaState.remoteStatus.collectAsState()
    val name by ImaaState.remoteName.collectAsState()
    val running by ImaaState.running.collectAsState()
    version.hashCode()

    fun restartIfRunning() {
        if (running) {
            GestureService.stop(context)
            GestureService.start(context)
        }
    }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.remote_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(stringResource(R.string.remote_body), color = MaterialTheme.colorScheme.onSurfaceVariant)
        SectionCard {
            Text(stringResource(R.string.remote_steps), style = MaterialTheme.typography.bodyMedium)
            OutlinedTextField(
                value = prefs.remoteHost,
                onValueChange = { prefs.remoteHost = it.trim() },
                label = { Text(stringResource(R.string.remote_host)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = prefs.remotePort.toString(),
                onValueChange = { v -> v.toIntOrNull()?.let { prefs.remotePort = it } },
                label = { Text(stringResource(R.string.remote_port)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = prefs.remoteCode,
                onValueChange = { v -> prefs.remoteCode = v.filter { it.isDigit() }.take(6) },
                label = { Text(stringResource(R.string.remote_code)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                modifier = Modifier.fillMaxWidth(),
            )
            ToggleRow(stringResource(R.string.remote_use), null, prefs.remoteEnabled) {
                prefs.remoteEnabled = it
                restartIfRunning()
            }
            val statusText = when (status) {
                "connecting" -> stringResource(R.string.remote_connecting)
                "connected" -> stringResource(R.string.remote_connected, name)
                "failed" -> stringResource(R.string.remote_failed)
                else -> stringResource(R.string.remote_off)
            }
            Text(statusText, color = if (status == "failed") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
