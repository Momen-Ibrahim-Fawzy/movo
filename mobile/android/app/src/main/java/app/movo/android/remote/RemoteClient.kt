package app.movo.android.remote

import android.net.Uri
import android.os.Build
import app.movo.android.core.GestureEvent
import app.movo.android.core.MovoState
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Sends recognised gesture names to the Movo desktop app on the local network (docs/REMOTE_PROTOCOL.md).
 * No images or other data are ever sent.
 */
class RemoteClient(private val host: String, private val port: Int, private val code: String) {
    private val client = OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS).connectTimeout(5, TimeUnit.SECONDS).build()
    private var socket: WebSocket? = null
    @Volatile private var authed = false
    @Volatile private var closed = false

    fun connect() {
        if (host.isBlank() || code.isBlank()) {
            MovoState.remoteStatus.value = "failed"
            return
        }
        MovoState.remoteStatus.value = "connecting"
        val request = Request.Builder().url("ws://$host:$port").build()
        socket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                val msg = runCatching { JSONObject(text) }.getOrNull() ?: return
                when (msg.optString("type")) {
                    "challenge" -> webSocket.send(
                        JSONObject()
                            .put("type", "auth")
                            .put("device", Build.MODEL ?: "Android")
                            .put("proof", proof(code, msg.optString("nonce")))
                            .toString(),
                    )
                    "welcome" -> {
                        authed = true
                        MovoState.remoteStatus.value = "connected"
                        MovoState.remoteName.value = host
                    }
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                authed = false
                MovoState.remoteStatus.value = if (closed) "off" else "failed"
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                authed = false
                MovoState.remoteStatus.value = if (closed || code == 1000) "off" else "failed"
            }
        })
    }

    fun sendGesture(ev: GestureEvent) {
        if (!authed) return
        socket?.send(
            JSONObject().put("type", "gesture").put("gesture", ev.gesture).put("phase", ev.phase).put("magnitude", ev.magnitude.toDouble()).toString(),
        )
    }

    fun close() {
        closed = true
        socket?.close(1000, "bye")
        socket = null
        MovoState.remoteStatus.value = "off"
    }

    companion object {
        fun proof(code: String, nonce: String): String {
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(SecretKeySpec(code.toByteArray(), "HmacSHA256"))
            return mac.doFinal(nonce.toByteArray()).joinToString("") { "%02x".format(it) }
        }

        /** Parses movo://pair?host=…&port=…&code=… */
        fun parsePairing(uri: Uri?): Triple<String, Int, String>? {
            if (uri == null || uri.scheme != "movo" || uri.host != "pair") return null
            val host = uri.getQueryParameter("host") ?: return null
            val port = uri.getQueryParameter("port")?.toIntOrNull() ?: 47813
            val code = uri.getQueryParameter("code") ?: return null
            return Triple(host, port, code)
        }
    }
}
