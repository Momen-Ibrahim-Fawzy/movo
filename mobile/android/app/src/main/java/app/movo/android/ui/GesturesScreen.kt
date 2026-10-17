package app.movo.android.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.movo.android.MovoApp
import app.movo.android.R
import app.movo.android.core.Catalog
import app.movo.android.core.GestureInfo

@Composable
fun GesturesScreen(modifier: Modifier) {
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val version by MovoApp.prefs.version.collectAsState()
    Column(modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = tab, containerColor = MaterialTheme.colorScheme.background) {
            Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text(stringResource(R.string.gestures_hand)) })
            Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text(stringResource(R.string.gestures_head)) })
            Tab(selected = tab == 2, onClick = { tab = 2 }, text = { Text(stringResource(R.string.gestures_eyes)) })
        }
        val list = when (tab) {
            0 -> Catalog.handGestures
            1 -> Catalog.headGestures
            else -> Catalog.eyeGestures
        }
        LazyColumn(
            Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 16.dp),
        ) {
            if (tab == 2) item { EyeSettingsCard() }
            items(list, key = { "${it.id}-$version" }) { GestureItem(it) }
        }
    }
}

@Composable
private fun GestureItem(g: GestureInfo) {
    val prefs = MovoApp.prefs
    SectionCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(g.emoji, fontSize = 30.sp)
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(stringResource(g.name), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                if (g.accurateOnly) {
                    Text(stringResource(R.string.gestures_accurate), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                }
            }
            Switch(checked = prefs.gestureEnabled(g.id), onCheckedChange = { prefs.setGestureEnabled(g.id, it) })
        }
        Dropdown(
            label = stringResource(R.string.gestures_does),
            options = Catalog.actions.map { it.id to "${it.emoji}  ${stringResource(it.label)}" },
            selected = prefs.binding(g.id),
            onSelect = { prefs.setBinding(g.id, it) },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
