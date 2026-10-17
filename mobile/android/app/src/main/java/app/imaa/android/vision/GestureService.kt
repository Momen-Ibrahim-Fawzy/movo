package app.imaa.android.vision

import android.app.Notification
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import app.imaa.android.ImaaApp
import app.imaa.android.R
import app.imaa.android.control.ActionRunner
import app.imaa.android.core.Catalog
import app.imaa.android.core.GestureEvent
import app.imaa.android.core.HandRecognizer
import app.imaa.android.core.HeadRecognizer
import app.imaa.android.core.ImaaState
import app.imaa.android.remote.RemoteClient
import app.imaa.android.ui.MainActivity
import com.google.mediapipe.framework.image.BitmapImageBuilder
import kotlinx.coroutines.launch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Foreground service that owns the camera. Frames are analysed in memory and released immediately;
 * nothing is stored or transmitted (the remote mode sends gesture names only).
 */
class GestureService : LifecycleService() {
    private lateinit var executor: ExecutorService
    private var provider: ProcessCameraProvider? = null
    private val main = Handler(Looper.getMainLooper())
    private val prefs get() = ImaaApp.prefs

    private val hand = HandRecognizer()
    private val head = HeadRecognizer()
    private var handTracker: HandTracker? = null
    private var faceTracker: FaceTracker? = null
    private var remote: RemoteClient? = null

    private var lastFrame = 0L
    private var lastSeen = 0L
    private var frameNo = 0L
    private var lastTs = 0L
    private val fpsWindow = ArrayDeque<Long>()
    private val startTime = SystemClock.uptimeMillis()

    override fun onCreate() {
        super.onCreate()
        executor = Executors.newSingleThreadExecutor()
        lifecycleScope.launch {
            ImaaState.recalibrate.collect { head.recalibrate() }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ACTION_STOP -> { stopSelf(); return START_NOT_STICKY }
            ACTION_TOGGLE_PAUSE -> { setPaused(!ImaaState.paused.value); return START_STICKY }
        }
        startInForeground()
        if (provider == null) startCamera()
        if (prefs.remoteEnabled && remote == null) {
            remote = RemoteClient(prefs.remoteHost, prefs.remotePort, prefs.remoteCode).also { it.connect() }
        }
        ImaaState.running.value = true
        lastSeen = SystemClock.uptimeMillis()
        return START_STICKY
    }

    private fun startInForeground() {
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA else 0
        ServiceCompat.startForeground(this, NOTIFICATION_ID, notification(), type)
    }

    private fun notification(): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val pauseIntent = PendingIntent.getService(
            this, 1, Intent(this, GestureService::class.java).setAction(ACTION_TOGGLE_PAUSE), PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this, 2, Intent(this, GestureService::class.java).setAction(ACTION_STOP), PendingIntent.FLAG_IMMUTABLE,
        )
        val paused = ImaaState.paused.value
        return NotificationCompat.Builder(this, ImaaApp.CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_imaa)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(getString(if (paused) R.string.notif_paused else R.string.notif_running))
            .setContentIntent(open)
            .setOngoing(true)
            .setSilent(true)
            .addAction(0, getString(if (paused) R.string.notif_resume else R.string.notif_pause), pauseIntent)
            .addAction(0, getString(R.string.notif_stop), stopIntent)
            .build()
    }

    private fun setPaused(paused: Boolean) {
        ImaaState.paused.value = paused
        ContextCompat.getSystemService(this, android.app.NotificationManager::class.java)?.notify(NOTIFICATION_ID, notification())
        ActionRunner.hud(this, getString(if (paused) R.string.hud_paused else R.string.hud_resumed))
    }

    private fun startCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            try {
                val p = future.get()
                provider = p
                val analysis = ImageAnalysis.Builder()
                    .setResolutionSelector(
                        ResolutionSelector.Builder()
                            .setResolutionStrategy(ResolutionStrategy(Size(640, 480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER))
                            .build(),
                    )
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                    .build()
                analysis.setAnalyzer(executor, ::analyze)
                val selector = if (p.hasCamera(CameraSelector.DEFAULT_FRONT_CAMERA)) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA
                p.unbindAll()
                p.bindToLifecycle(this, selector, analysis)
                ImaaState.error.value = null
            } catch (e: Exception) {
                Log.e(TAG, "camera failed", e)
                ImaaState.error.value = getString(R.string.error_camera)
                stopSelf()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun analyze(proxy: ImageProxy) {
        proxy.use { image ->
            val now = SystemClock.uptimeMillis()
            val idle = now - lastSeen > 3000
            val target = if (idle) 5 else prefs.targetFps()
            if (now - lastFrame < 1000L / target) return
            lastFrame = now
            try {
                process(image, now, idle)
            } catch (e: Exception) {
                Log.e(TAG, "frame failed", e)
            }
        }
    }

    private fun process(image: ImageProxy, now: Long, idle: Boolean) {
        val handOn = prefs.handEnabled
        val headOn = prefs.headEnabled
        val accurate = prefs.headMode == "accurate"
        if (handOn && handTracker == null) handTracker = HandTracker(this)
        if (!handOn) { handTracker?.close(); handTracker = null; hand.reset() }
        if (faceTracker != null && faceTracker!!.accurate != accurate) { faceTracker?.close(); faceTracker = null; head.recalibrate() }
        if (headOn && faceTracker == null) faceTracker = FaceTracker(this, accurate)
        if (!headOn) { faceTracker?.close(); faceTracker = null }
        hand.holdScale = prefs.holdScale
        head.sensitivity = prefs.headSensitivity

        // Upright + mirrored (what the user sees), in one pass.
        val src = image.toBitmap()
        val matrix = Matrix().apply {
            postRotate(image.imageInfo.rotationDegrees.toFloat())
            postScale(-1f, 1f)
        }
        val bitmap = Bitmap.createBitmap(src, 0, 0, src.width, src.height, matrix, false)
        val mp = BitmapImageBuilder(bitmap).build()
        val aspect = bitmap.width.toFloat() / bitmap.height
        val ts = maxOf(now, lastTs + 1).also { lastTs = it }
        val t = (now - startTime) / 1000f

        val runHand = handTracker != null && (faceTracker == null || frameNo % 2 == 0L)
        val runFace = faceTracker != null && (handTracker == null || frameNo % 2 == 1L)
        frameNo++
        val events = mutableListOf<GestureEvent>()
        var present = false
        if (runHand) {
            val lm = handTracker!!.detect(mp, ts, aspect)
            present = lm != null
            events += hand.update(lm, t)
        }
        if (runFace) {
            val obs = faceTracker!!.detect(mp, ts, aspect)
            present = present || obs != null
            events += head.update(obs, t)
        }
        if (present) lastSeen = now
        mp.close()
        bitmap.recycle()
        if (src !== bitmap) src.recycle()

        fpsWindow.addLast(now)
        while (fpsWindow.isNotEmpty() && now - fpsWindow.first() > 1000) fpsWindow.removeFirst()
        ImaaState.fps.value = fpsWindow.size
        ImaaState.idle.value = idle
        ImaaState.livePose.value = hand.livePose ?: head.livePose
        events.forEach { ev -> main.post { dispatch(ev) } }
    }

    private fun dispatch(ev: GestureEvent) {
        if (!prefs.gestureEnabled(ev.gesture)) return
        val action = prefs.binding(ev.gesture)
        if (prefs.practice) {
            if (ev.phase == "start") ActionRunner.hud(this, "${Catalog.gestures[ev.gesture]?.emoji ?: ""} ${getString(Catalog.gestures[ev.gesture]!!.name)}")
            return
        }
        if (action == "pause_control") {
            if (ev.phase == "start") setPaused(!ImaaState.paused.value)
            return
        }
        if (ImaaState.paused.value || action == "none") return
        val client = remote
        if (client != null && prefs.remoteEnabled) {
            client.sendGesture(ev)
            return
        }
        val info = Catalog.actionsById[action] ?: return
        if (ev.phase == "repeat" && !info.repeatable) return
        ActionRunner.run(this, action, ev.magnitude)
    }

    override fun onDestroy() {
        provider?.unbindAll()
        executor.execute {
            handTracker?.close(); handTracker = null
            faceTracker?.close(); faceTracker = null
        }
        executor.shutdown()
        remote?.close()
        remote = null
        ImaaState.running.value = false
        ImaaState.paused.value = false
        ImaaState.livePose.value = null
        super.onDestroy()
    }

    companion object {
        private const val TAG = "ImaaGesture"
        private const val NOTIFICATION_ID = 7
        const val ACTION_STOP = "app.imaa.android.STOP"
        const val ACTION_TOGGLE_PAUSE = "app.imaa.android.TOGGLE_PAUSE"

        fun start(context: Context) = ContextCompat.startForegroundService(context, Intent(context, GestureService::class.java))

        fun stop(context: Context) = context.stopService(Intent(context, GestureService::class.java))

        fun togglePause(context: Context) =
            context.startService(Intent(context, GestureService::class.java).setAction(ACTION_TOGGLE_PAUSE))
    }
}
