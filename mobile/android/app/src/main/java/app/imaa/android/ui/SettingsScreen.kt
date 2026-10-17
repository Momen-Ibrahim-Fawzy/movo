package app.imaa.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import app.imaa.android.BuildConfig
import app.imaa.android.ImaaApp
import app.imaa.android.R
import app.imaa.android.core.ImaaState

@Composable
fun SettingsScreen(modifier: Modifier, onLanguage: (String) -> Unit) {
    val prefs = ImaaApp.prefs
    val version by prefs.version.collectAsState()
    version.hashCode()
    val system = stringResource(R.string.settings_system)

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        SectionCard(stringResource(R.string.settings_appearance)) {
            Dropdown(
                stringResource(R.string.settings_language),
                listOf("system" to system, "en" to "English", "ar" to "العربية"),
                prefs.language,
                onLanguage,
                Modifier.fillMaxWidth(),
            )
            Dropdown(
                stringResource(R.string.settings_theme),
                listOf("system" to system, "light" to stringResource(R.string.settings_light), "dark" to stringResource(R.string.settings_dark)),
                prefs.theme,
                { prefs.theme = it },
                Modifier.fillMaxWidth(),
            )
        }

        SectionCard(stringResource(R.string.settings_detection)) {
            Dropdown(
                stringResource(R.string.settings_power),
                listOf(
                    "eco" to stringResource(R.string.settings_power_eco),
                    "balanced" to stringResource(R.string.settings_power_balanced),
                    "performance" to stringResource(R.string.settings_power_performance),
                ),
                prefs.powerMode,
                { prefs.powerMode = it },
                Modifier.fillMaxWidth(),
            )
            Text(stringResource(R.string.settings_hold), style = MaterialTheme.typography.bodyMedium)
            Slider(value = prefs.holdScale, onValueChange = { prefs.holdScale = it }, valueRange = 0.5f..2f)
            Dropdown(
                stringResource(R.string.settings_head_mode),
                listOf("light" to stringResource(R.string.settings_head_light), "accurate" to stringResource(R.string.settings_head_accurate)),
                prefs.headMode,
                { prefs.headMode = it },
                Modifier.fillMaxWidth(),
            )
            Text(stringResource(R.string.settings_head_sens), style = MaterialTheme.typography.bodyMedium)
            Slider(value = prefs.headSensitivity, onValueChange = { prefs.headSensitivity = it }, valueRange = 0.6f..1.8f)
            OutlinedButton(onClick = { ImaaState.recalibrate.value = ImaaState.recalibrate.value + 1 }) {
                Text(stringResource(R.string.settings_recalibrate))
            }
        }

        SectionCard(stringResource(R.string.settings_privacy)) {
            Text(stringResource(R.string.settings_privacy_text), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        SectionCard(stringResource(R.string.settings_about)) {
            Text(stringResource(R.string.settings_version, BuildConfig.VERSION_NAME))
            Text(stringResource(R.string.settings_meaning), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
