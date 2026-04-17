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
            onComplete?.invoke(false, message)
            return
        }

        executor.execute {
            val result = runCatching {
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

            val ok = result.startsWith("Uploaded")
            Prefs.setLastStatus(context, result)
            onComplete?.invoke(ok, result)
        }
    }
}
