package app.imaa.android.ui

import android.media.AudioManager
import android.media.ToneGenerator
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import app.imaa.android.ImaaApp
import app.imaa.android.R
import app.imaa.android.core.Eyes
import app.imaa.android.core.ImaaState
import kotlinx.coroutines.delay

@Composable
fun EyeSettingsCard() {
    val prefs = ImaaApp.prefs
    val open by ImaaState.eyeOpen.collectAsState()
    val running by ImaaState.running.collectAsState()
    var calibrating by remember { mutableStateOf(false) }
    SectionCard {
        Text(stringResource(R.string.eyes_intro), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        ToggleRow(stringResource(R.string.home_eyes), stringResource(R.string.home_eyes_d), prefs.eyesEnabled) { prefs.eyesEnabled = it }
        ToggleRow(stringResource(R.string.eyes_glasses), stringResource(R.string.eyes_glasses_d), prefs.eyesGlasses) { prefs.eyesGlasses = it }
        Text(stringResource(R.string.eyes_sensitivity), style = MaterialTheme.typography.bodyMedium)
        Slider(value = prefs.eyesSensitivity, onValueChange = { prefs.eyesSensitivity = it }, valueRange = 0.6f..1.6f)
        if (running && prefs.eyesEnabled) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                listOf(R.string.eyes_left to open[0], R.string.eyes_right to open[1]).forEach { (label, v) ->
                    Column(Modifier.weight(1f)) {
                        Text(stringResource(label), style = MaterialTheme.typography.labelSmall)
                        LinearProgressIndicator(progress = { v.coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth())
                    }
                }
            }
        }
        Text(
            stringResource(if (prefs.eyesCalibration.isNotEmpty()) R.string.eyes_cal_done_status else R.string.eyes_cal_auto_status),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { calibrating = true }, enabled = running && prefs.eyesEnabled) { Text(stringResource(R.string.eyes_calibrate)) }
            if (prefs.eyesCalibration.isNotEmpty()) {
                OutlinedButton(onClick = { prefs.eyesCalibration = ""; Eyes.recognizer.calibration = null }) { Text(stringResource(R.string.eyes_reset)) }
            }
        }
    }
    if (calibrating) CalibrationDialog { calibrating = false }
}

@Composable
private fun CalibrationDialog(onClose: () -> Unit) {
    var step by remember { mutableStateOf(0) } // 0 ready, 1 open, 2 closed, 3 done, 4 failed
    var progress by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(Unit) {
        val tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)
        val eyes = Eyes.recognizer
        suspend fun phase(seconds: Float) {
            val steps = (seconds * 20).toInt()
            for (i in 0..steps) { progress = i / steps.toFloat(); delay(50) }
        }
        phase(3f)
        step = 1; eyes.beginCapture("open"); phase(2f)
        tone.startTone(ToneGenerator.TONE_PROP_BEEP, 150)
        step = 2; eyes.beginCapture("closed"); phase(2.5f)
        eyes.endCapture()
        tone.startTone(ToneGenerator.TONE_PROP_ACK, 200)
        val cal = eyes.finishCalibration()
        if (cal != null) ImaaApp.prefs.eyesCalibration = cal.encode()
        step = if (cal != null) 3 else 4
        delay(300)
        tone.release()
    }
    val (title, body) = when (step) {
        0 -> R.string.eyes_cal_ready to R.string.eyes_cal_ready_d
        1 -> R.string.eyes_cal_open to R.string.eyes_cal_open_d
        2 -> R.string.eyes_cal_closed to R.string.eyes_cal_closed_d
        3 -> R.string.eyes_cal_ok to R.string.eyes_cal_ok_d
        else -> R.string.eyes_cal_failed to R.string.eyes_cal_failed_d
    }
    AlertDialog(
        onDismissRequest = { if (step >= 3) onClose() },
        title = { Text(stringResource(title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(stringResource(body))
                if (step < 3) LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = { if (step >= 3) TextButton(onClick = onClose) { Text(stringResource(R.string.eyes_cal_close)) } },
    )
}
