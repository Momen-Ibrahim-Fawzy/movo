package app.imaa.android.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import app.imaa.android.ImaaApp
import app.imaa.android.R
import app.imaa.android.core.Catalog
import app.imaa.android.core.ImaaState
import app.imaa.android.vision.GestureService

@Composable
fun HomeScreen(modifier: Modifier, onOpenAccessibility: () -> Unit) {
    val context = LocalContext.current
    val prefs = ImaaApp.prefs
    val version by prefs.version.collectAsState()
    val running by ImaaState.running.collectAsState()
    val paused by ImaaState.paused.collectAsState()
    val pose by ImaaState.livePose.collectAsState()
    val last by ImaaState.lastAction.collectAsState()
    val fps by ImaaState.fps.collectAsState()
    val idle by ImaaState.idle.collectAsState()
    val accessibilityOn by ImaaState.accessibilityOn.collectAsState()
    val error by ImaaState.error.collectAsState()
    var showDisclosure by remember { mutableStateOf(false) }
    version.hashCode()

    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        if (result[Manifest.permission.CAMERA] == true) GestureService.start(context)
    }

    fun toggle() {
        if (running) {
            GestureService.stop(context)
            return
        }
        val needed = buildList {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) add(Manifest.permission.CAMERA)
            if (Build.VERSION.SDK_INT >= 33 &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (needed.isEmpty()) GestureService.start(context) else permissions.launch(needed.toTypedArray())
    }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            LogoMark(44.dp)
            Spacer(Modifier.width(12.dp))
            Column {
                Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(stringResource(R.string.tagline), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }

        SectionCard {
            Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                PowerButton(running, stringResource(if (running) R.string.notif_stop else R.string.state_stopped), ::toggle)
                val state = when {
                    !running -> R.string.state_stopped
                    paused -> R.string.state_paused
                    else -> R.string.state_running
                }
                Text(stringResource(state), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                val detail = when {
                    error != null -> error!!
                    !running -> stringResource(R.string.state_stopped_d)
                    paused -> stringResource(R.string.state_paused_d)
                    prefs.remoteEnabled -> stringResource(R.string.state_remote_d)
                    else -> stringResource(R.string.state_running_d)
                }
                Text(detail, textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
                if (running) {
                    val g = pose?.let { Catalog.gestures[it] }
                    val seeing = g?.let { "${it.emoji}  ${stringResource(it.name)}" } ?: "—"
                    Text("${stringResource(R.string.home_seeing)}: $seeing", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        stringResource(R.string.home_fps, fps) + if (idle) " · " + stringResource(R.string.home_idle) else "",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    OutlinedButton(onClick = { GestureService.togglePause(context) }) {
                        Text(stringResource(if (paused) R.string.home_resume else R.string.home_pause))
                    }
                }
            }
        }

        SectionCard(stringResource(R.string.home_control_title)) {
            Text(
                stringResource(if (accessibilityOn) R.string.home_control_on else R.string.home_control_off),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodyMedium,
            )
            if (!accessibilityOn) {
                Button(onClick = { if (prefs.disclosureAccepted) onOpenAccessibility() else showDisclosure = true }) {
                    Text(stringResource(R.string.home_control_button))
                }
            }
        }

        SectionCard(stringResource(R.string.home_quick)) {
            ToggleRow(stringResource(R.string.home_hand), null, prefs.handEnabled) { prefs.handEnabled = it }
            ToggleRow(stringResource(R.string.home_head), null, prefs.headEnabled) { prefs.headEnabled = it }
            ToggleRow(stringResource(R.string.home_practice), stringResource(R.string.home_practice_d), prefs.practice) { prefs.practice = it }
            ToggleRow(stringResource(R.string.home_hud), null, prefs.hudEnabled) { prefs.hudEnabled = it }
        }

        SectionCard(stringResource(R.string.home_last)) {
            Text(last ?: stringResource(R.string.home_nothing), style = MaterialTheme.typography.bodyLarge)
        }

        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(horizontal = 4.dp)) {
            Icon(Icons.Outlined.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(stringResource(R.string.home_privacy), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }

    if (showDisclosure) {
        AlertDialog(
            onDismissRequest = { showDisclosure = false },
            title = { Text(stringResource(R.string.disclosure_title)) },
            text = { Text(stringResource(R.string.disclosure_body)) },
            confirmButton = {
                TextButton(onClick = {
                    prefs.disclosureAccepted = true
                    showDisclosure = false
                    onOpenAccessibility()
                }) { Text(stringResource(R.string.disclosure_agree)) }
            },
            dismissButton = { TextButton(onClick = { showDisclosure = false }) { Text(stringResource(R.string.disclosure_cancel)) } },
        )
    }
}
