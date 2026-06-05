package com.cybermzazi.companion

import android.content.Context
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.net.UnknownHostException
import java.util.concurrent.Executors

object IngestionClient {
    private val executor = Executors.newSingleThreadExecutor()

    fun sendNotification(
        context: Context,
        payload: NotificationPayload,
        onComplete: ((Boolean, String) -> Unit)? = null,
    ) {
        if (!Prefs.isChildSignedIn(context)) {
            val message = "Child is signed out. Notification upload paused."
            Prefs.setLastStatus(context, message)
            onComplete?.invoke(false, message)
            return
        }
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val token = Prefs.getDeviceToken(context).trim()
        val payloads = splitPayload(payload)
        if (baseUrl.isBlank() || token.isBlank()) {
            val message = "Pair this device first."
            Prefs.setLastStatus(context, message)
            payloads.forEach { NotificationQueueStore.enqueue(context, it) }
            RecentNotificationLog.append(context, payload.appName, payload.notificationTitle, payload.notificationText, "Queued: missing settings")
            onComplete?.invoke(false, message)
            return
        }

        executor.execute {
            var sentCount = 0
            val failed = mutableListOf<NotificationPayload>()
            var lastResult = ""
            payloads.forEach { item ->
                val result = upload(context, baseUrl, token, item)
                lastResult = result
                if (result.startsWith("Uploaded")) {
                    sentCount += 1
                    RecentNotificationLog.append(context, item.appName, item.notificationTitle, item.notificationText, result)
                } else {
                    failed += item
                    NotificationQueueStore.enqueue(context, item)
                    RecentNotificationLog.append(context, item.appName, item.notificationTitle, item.notificationText, "Queued: $result")
                }
            }
            val ok = failed.isEmpty()
            val result = if (payloads.size == 1) {
                lastResult
            } else {
                "Uploaded $sentCount of ${payloads.size} notification message(s)."
            }
            if (ok) flushQueuedNotifications(context)
            Prefs.setLastStatus(context, result)
            onComplete?.invoke(ok, result)
        }
    }

    fun flushQueuedNotifications(
        context: Context,
        onComplete: ((Boolean, String) -> Unit)? = null,
    ) {
        if (!Prefs.isChildSignedIn(context)) {
            onComplete?.invoke(false, "Child is signed out. Notification upload paused.")
            return
        }
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val token = Prefs.getDeviceToken(context).trim()
        if (baseUrl.isBlank() || token.isBlank()) {
            onComplete?.invoke(false, "Pair this device first.")
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
                val result = upload(context, baseUrl, token, payload)
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

    private fun upload(context: Context, baseUrl: String, token: String, payload: NotificationPayload): String =
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
            } else if (responseCode == 401) {
                Prefs.setDeviceToken(context, "")
                context.getString(R.string.upload_failed_pair_again)
            } else {
                val errorText = runCatching {
                    connection.errorStream?.bufferedReader()?.use { it.readText() }.orEmpty()
                }.getOrDefault("").trim()
                if (errorText.isNotBlank()) {
                    "Upload failed with HTTP $responseCode: ${errorText.take(120)}"
                } else {
                    "Upload failed with HTTP $responseCode"
                }
            }
        }.getOrElse { throwable ->
            if (throwable is UnknownHostException) {
                context.getString(R.string.upload_failed_network_dns)
            } else {
                "Upload error: ${throwable.message ?: "Unknown error"}"
            }
        }

    private fun splitPayload(payload: NotificationPayload): List<NotificationPayload> {
        val normalized = payload.notificationText
            .replace("\r\n", "\n")
            .replace('\r', '\n')
            .trim()
        val parts = normalized
            .split('\n')
            .map { it.trim() }
            .filter { it.length >= 2 }
            .distinct()
        val messages = if (parts.size > 1) parts else listOf(normalized)
        return messages.take(300).map { text ->
            payload.copy(notificationText = text)
        }
    }
}
