package app.movo.android.control

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Color
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.util.TypedValue
import android.view.Gravity
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.TextView
import app.movo.android.core.MovoState

/**
 * Accessibility service that performs the gestures the user asks for. It never reads screen content except to
 * find a visible "Skip ad" button when the user makes the skip gesture.
 */
class ControlService : AccessibilityService() {
    private val main = Handler(Looper.getMainLooper())
    private var hud: TextView? = null
    private val hideHud = Runnable { hud?.animate()?.alpha(0f)?.setDuration(300)?.start() }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        MovoState.accessibilityOn.value = true
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        hud?.let { runCatching { (getSystemService(WINDOW_SERVICE) as WindowManager).removeView(it) } }
        hud = null
        instance = null
        MovoState.accessibilityOn.value = false
        super.onDestroy()
    }

    // ------------------------------------------------------------------ gestures
    private val screen: Rect
        get() {
            val wm = getSystemService(WINDOW_SERVICE) as WindowManager
            return if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
                wm.currentWindowMetrics.bounds
            } else {
                val dm = resources.displayMetrics
                Rect(0, 0, dm.widthPixels, dm.heightPixels)
            }
        }

    fun swipe(fromX: Float, fromY: Float, toX: Float, toY: Float, durationMs: Long = 220): Boolean {
        val r = screen
        val path = Path().apply {
            moveTo(r.width() * fromX, r.height() * fromY)
            lineTo(r.width() * toX, r.height() * toY)
        }
        return dispatchGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, durationMs)).build(), null, null)
    }

    fun tap(x: Float = 0.5f, y: Float = 0.5f): Boolean {
        val r = screen
        val path = Path().apply { moveTo(r.width() * x, r.height() * y) }
        return dispatchGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, 40)).build(), null, null)
    }

    fun tapAt(px: Float, py: Float): Boolean {
        val path = Path().apply { moveTo(px, py) }
        return dispatchGesture(GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, 40)).build(), null, null)
    }

    /** Two-finger pinch around the centre: out = zoom in. */
    fun pinch(out: Boolean): Boolean {
        val r = screen
        val cx = r.width() / 2f
        val cy = r.height() / 2f
        val near = r.width() * 0.08f
        val far = r.width() * 0.30f
        val (a, b) = if (out) near to far else far to near
        val p1 = Path().apply { moveTo(cx - a, cy - a); lineTo(cx - b, cy - b) }
        val p2 = Path().apply { moveTo(cx + a, cy + a); lineTo(cx + b, cy + b) }
        val g = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(p1, 0, 280))
            .addStroke(GestureDescription.StrokeDescription(p2, 0, 280))
            .build()
        return dispatchGesture(g, null, null)
    }

    fun global(action: Int): Boolean = performGlobalAction(action)

    // ------------------------------------------------------------------ skip ad
    fun skipAd(): Boolean {
        val roots = buildList {
            rootInActiveWindow?.let { add(it) }
            runCatching { windows.mapNotNull { it.root } }.getOrNull()?.let { addAll(it) }
        }
        for (root in roots) {
            val node = find(root, 0) ?: continue
            var target: AccessibilityNodeInfo? = node
            while (target != null && !target.isClickable) target = target.parent
            if (target != null && target.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
            val r = Rect().also { node.getBoundsInScreen(it) }
            if (!r.isEmpty) return tapAt(r.exactCenterX(), r.exactCenterY())
        }
        return false
    }

    private fun find(node: AccessibilityNodeInfo, depth: Int): AccessibilityNodeInfo? {
        if (depth > 40) return null
        val text = (node.text ?: node.contentDescription)?.toString()?.trim().orEmpty()
        if (text.length in 1..30 && SKIP.matches(text) && node.isVisibleToUser) return node
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            find(child, depth + 1)?.let { return it }
        }
        return null
    }

    // ------------------------------------------------------------------ HUD
    fun showHud(text: String) {
        main.post {
            val wm = getSystemService(WINDOW_SERVICE) as WindowManager
            val view = hud ?: TextView(this).also { tv ->
                tv.setTextColor(Color.WHITE)
                tv.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
                val pad = (14 * resources.displayMetrics.density).toInt()
                tv.setPadding(pad * 2, pad, pad * 2, pad)
                tv.background = GradientDrawable().apply {
                    cornerRadius = 999f
                    setColor(Color.argb(225, 18, 20, 28))
                }
                val lp = WindowManager.LayoutParams(
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                    PixelFormat.TRANSLUCENT,
                ).apply {
                    gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
                    y = (96 * resources.displayMetrics.density).toInt()
                }
                wm.addView(tv, lp)
                hud = tv
            }
            view.text = text
            view.animate().cancel()
            view.alpha = 1f
            main.removeCallbacks(hideHud)
            main.postDelayed(hideHud, 1300)
        }
    }

    companion object {
        @Volatile
        var instance: ControlService? = null
            private set

        val SKIP = Regex(
            "^\\s*(skip(\\s+ads?)?|skip\\s+ad\\s*now|تخط[يّ]+(\\s+الإعلان(ات)?)?|تجاوز(\\s+الإعلان)?|passer(\\s+l['’]annonce)?|" +
                "omitir(\\s+anuncios?)?|(werbung\\s+)?überspringen|pular(\\s+anúncios?)?|salta(\\s+annunci)?|reklam[ıi]\\s+geç|atla)" +
                "\\s*[›>»▶]*\\s*$",
            RegexOption.IGNORE_CASE,
        )
    }
}
