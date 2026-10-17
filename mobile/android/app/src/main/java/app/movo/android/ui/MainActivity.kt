package app.movo.android.ui

import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Cast
import androidx.compose.material.icons.outlined.HelpOutline
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.PanTool
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.core.os.LocaleListCompat
import app.movo.android.MovoApp
import app.movo.android.R
import app.movo.android.control.ControlService
import app.movo.android.core.MovoState
import app.movo.android.remote.RemoteClient
import app.movo.android.ui.theme.MovoTheme
import kotlinx.coroutines.flow.MutableStateFlow

class MainActivity : AppCompatActivity() {
    private val pairing = MutableStateFlow(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handlePairing(intent)
        setContent {
            val prefs = MovoApp.prefs
            val version by prefs.version.collectAsState()
            val paired by pairing.collectAsState()
            val snackbar = remember { SnackbarHostState() }
            var tab by rememberSaveable { mutableIntStateOf(0) }
            val pairedText = stringResource(R.string.remote_paired)
            LaunchedEffect(paired) {
                if (paired > 0) {
                    tab = 2
                    snackbar.showSnackbar(pairedText)
                }
            }
            MovoTheme(theme = prefs.theme.also { version.hashCode() }) {
                Scaffold(
                    containerColor = MaterialTheme.colorScheme.background,
                    snackbarHost = { SnackbarHost(snackbar) },
                    bottomBar = {
                        NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                            val items = listOf(
                                Icons.Outlined.Home to R.string.nav_home,
                                Icons.Outlined.PanTool to R.string.nav_gestures,
                                Icons.Outlined.Cast to R.string.nav_remote,
                                Icons.Outlined.HelpOutline to R.string.nav_help,
                                Icons.Outlined.Settings to R.string.nav_settings,
                            )
                            items.forEachIndexed { i, (icon, label) ->
                                NavigationBarItem(
                                    selected = tab == i,
                                    onClick = { tab = i },
                                    icon = { Icon(icon, contentDescription = null) },
                                    label = { Text(stringResource(label)) },
                                )
                            }
                        }
                    },
                ) { padding ->
                    val m = Modifier.padding(padding)
                    when (tab) {
                        0 -> HomeScreen(m, onOpenAccessibility = ::openAccessibilitySettings)
                        1 -> GesturesScreen(m)
                        2 -> RemoteScreen(m)
                        3 -> HelpScreen(m)
                        else -> SettingsScreen(m, onLanguage = ::setLanguage)
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handlePairing(intent)
    }

    override fun onResume() {
        super.onResume()
        MovoState.accessibilityOn.value = ControlService.instance != null || isAccessibilityEnabled()
    }

    private fun handlePairing(intent: Intent?) {
        val (host, port, code) = RemoteClient.parsePairing(intent?.data) ?: return
        MovoApp.prefs.remoteHost = host
        MovoApp.prefs.remotePort = port
        MovoApp.prefs.remoteCode = code
        pairing.value = pairing.value + 1
    }

    private fun isAccessibilityEnabled(): Boolean {
        val enabled = Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
        val me = ComponentName(this, ControlService::class.java).flattenToString()
        return enabled.split(':').any { it.equals(me, ignoreCase = true) }
    }

    private fun openAccessibilitySettings() {
        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    private fun setLanguage(tag: String) {
        MovoApp.prefs.language = tag
        AppCompatDelegate.setApplicationLocales(
            if (tag == "system") LocaleListCompat.getEmptyLocaleList() else LocaleListCompat.forLanguageTags(tag),
        )
    }
}
