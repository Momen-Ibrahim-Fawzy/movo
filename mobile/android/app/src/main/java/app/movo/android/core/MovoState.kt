package app.movo.android.core

import kotlinx.coroutines.flow.MutableStateFlow

/** Live state shared between the camera service and the UI (in-process only). */
object MovoState {
    val running = MutableStateFlow(false)
    val paused = MutableStateFlow(false)
    val livePose = MutableStateFlow<String?>(null)
    val lastAction = MutableStateFlow<String?>(null)
    val fps = MutableStateFlow(0)
    val idle = MutableStateFlow(false)
    val error = MutableStateFlow<String?>(null)
    val remoteStatus = MutableStateFlow("off") // off | connecting | connected | failed
    val remoteName = MutableStateFlow("")
    val accessibilityOn = MutableStateFlow(false)
    val recalibrate = MutableStateFlow(0)
    val eyeOpen = MutableStateFlow(listOf(1f, 1f))
}
