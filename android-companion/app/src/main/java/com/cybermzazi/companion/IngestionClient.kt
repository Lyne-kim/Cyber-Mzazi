package com.cybermzazi.companion

import android.content.Context
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

object IngestionClient {
    private val executor = Executors.newSingleThreadExecutor()

    fun sendNotification(
        context: Context,
        payload: NotificationPayload,
        onComplete: ((Boolean, String) -> Unit)? = null,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val token = Prefs.getDeviceToken(context).trim()
        if (baseUrl.isBlank() || token.isBlank()) {
            val message = "Save the backend URL and device token first."
            Prefs.setLastStatus(context, message)
            NotificationQueueStore.enqueue(context, payload)
            RecentNotificationLog.append(context, payload.appName, payload.notificationTitle, payload.notificationText, "Queued: missing settings")
            onComplete?.invoke(false, message)
            return
        }

        executor.execute {
            val result = upload(baseUrl, token, payload)
            val ok = result.startsWith("Uploaded")
            if (ok) {
                RecentNotificationLog.append(context, payload.appName, payload.notificationTitle, payload.notificationText, result)
                flushQueuedNotifications(context)
            } else {
                NotificationQueueStore.enqueue(context, payload)
                RecentNotificationLog.append(context, payload.appName, payload.notificationTitle, payload.notificationText, "Queued: $result")
            }
            Prefs.setLastStatus(context, result)
            onComplete?.invoke(ok, result)
        }
    }

    fun flushQueuedNotifications(
        context: Context,
        onComplete: ((Boolean, String) -> Unit)? = null,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val token = Prefs.getDeviceToken(context).trim()
        if (baseUrl.isBlank() || token.isBlank()) {
            onComplete?.invoke(false, "Save the backend URL and device token first.")
            return
        }
        executor.execute {
            val queue = NotificationQueueStore.getQueue(context).toMutableList()
            if (queue.isEmpty()) {
                val message = "No queued notifications."
                Prefs.setLastStatus(context, message)
                onComplete?.invoke(true, message)
                return@execute
            }

            val remaining = mutableListOf<NotificationPayload>()
            var sentCount = 0
            queue.forEach { payload ->
                val result = upload(baseUrl, token, payload)
                if (result.startsWith("Uploaded")) {
                    sentCount += 1
                    RecentNotificationLog.append(context, payload.appName, payload.notificationTitle, payload.notificationText, "Retried: $result")
                } else {
                    remaining += payload
                }
            }
            NotificationQueueStore.replace(context, remaining)
            val message = if (remaining.isEmpty()) {
                "Retried queued notifications successfully: $sentCount sent."
            } else {
                "Retried queue: $sentCount sent, ${remaining.size} still queued."
            }
            Prefs.setLastStatus(context, message)
            onComplete?.invoke(remaining.isEmpty(), message)
        }
    }

    private fun upload(baseUrl: String, token: String, payload: NotificationPayload): String =
        runCatching {
            val url = URL("$baseUrl/api/device-ingest/android-notifications")
            val connection = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 15000
                readTimeout = 15000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Authorization", "Bearer $token")
            }

            val body = JSONObject().apply {
                put("app_name", payload.appName)
                put("app_package", payload.appPackage)
                put("sender_handle", payload.senderHandle)
                put("notification_title", payload.notificationTitle)
                put("notification_text", payload.notificationText)
                put("deep_link", payload.deepLink)
            }

            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(body.toString())
            }

            val responseCode = connection.responseCode
            if (responseCode in 200..299) {
                "Uploaded $responseCode from ${payload.appName}"
            } else {
                "Upload failed with HTTP $responseCode"
            }
        }.getOrElse { throwable ->
            "Upload error: ${throwable.message ?: "Unknown error"}"
        }
}
