package com.cybermzazi.companion

import android.content.Context
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

object ParentApiClient {
    private val executor = Executors.newSingleThreadExecutor()
    private var latestFlaggedMessageId: Int? = null
    private var pendingLogoutRequestId: Int? = null
    private var latestPairingUri: String = ""

    fun login(
        context: Context,
        identifier: String,
        password: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            onComplete(false, "Save the backend URL first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/auth/login").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 15000
                    readTimeout = 15000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                }
                val body = JSONObject().apply {
                    put("portal", "parent")
                    put("identifier", identifier)
                    put("password", password)
                }
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body.toString())
                }
                val response = readResponse(connection)
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Parent sign-in failed."))
                }
                val cookie = connection.headerFields["Set-Cookie"]
                    ?.firstOrNull()
                    ?.substringBefore(";")
                    .orEmpty()
                if (cookie.isBlank()) {
                    return@runCatching ParentApiResult(false, "Parent sign-in did not return a session.")
                }
                Prefs.setParentIdentifier(context, identifier)
                Prefs.setParentSessionCookie(context, cookie)
                ParentApiResult(true, "Parent sign-in ready.")
            }.getOrElse { throwable ->
                ParentApiResult(false, "Parent sign-in error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

    fun registerFamily(
        context: Context,
        familyName: String,
        parentName: String,
        parentContact: String,
        parentPassword: String,
        childName: String,
        childUsername: String,
        childPassword: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postPublicJson(
            context = context,
            path = "/api/auth/register",
            body = JSONObject()
                .put("family_name", familyName)
                .put("parent_name", parentName)
                .put("parent_contact", parentContact)
                .put("parent_password", parentPassword)
                .put("child_name", childName)
                .put("child_username", childUsername)
                .put("child_password", childPassword),
            successMessage = "Family account created. Verify the parent contact before signing in.",
            onComplete = onComplete,
        )
    }

    fun childLogin(
        context: Context,
        parentContact: String,
        childUsername: String,
        password: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            onComplete(false, "Save the backend URL first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/auth/login").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 15000
                    readTimeout = 15000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                }
                val body = JSONObject().apply {
                    put("portal", "child")
                    put("parent_contact", parentContact)
                    put("child_username", childUsername)
                    put("password", password)
                }
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body.toString())
                }
                val response = readResponse(connection)
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Child sign-in failed."))
                }
                ParentApiResult(true, "Child sign-in ready.")
            }.getOrElse { throwable ->
                ParentApiResult(false, "Child sign-in error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

    fun resendPhoneVerification(
        context: Context,
        identifier: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postPublicJson(
            context = context,
            path = "/api/auth/resend-phone-verification",
            body = JSONObject().put("identifier", identifier),
            successMessage = "Phone verification code sent.",
            onComplete = onComplete,
        )
    }

    fun verifyPhone(
        context: Context,
        identifier: String,
        code: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postPublicJson(
            context = context,
            path = "/api/auth/verify-phone",
            body = JSONObject()
                .put("identifier", identifier)
                .put("code", code),
            successMessage = "Phone number verified. Sign in again to continue.",
            onComplete = onComplete,
        )
    }

    fun fetchAlerts(context: Context, onComplete: (Boolean, String) -> Unit) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val cookie = Prefs.getParentSessionCookie(context)
        if (baseUrl.isBlank()) {
            onComplete(false, "Save the backend URL first.")
            return
        }
        if (cookie.isBlank()) {
            onComplete(false, "Sign in as parent to load native alerts.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/parent/alerts").openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 15000
                    readTimeout = 15000
                    setRequestProperty("Cookie", cookie)
                    setRequestProperty("Accept", "application/json")
                }
                val response = readResponse(connection)
                if (connection.responseCode == 401 || connection.responseCode == 403) {
                    Prefs.clearParentSession(context)
                    return@runCatching ParentApiResult(false, "Parent session expired. Sign in again.")
                }
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Could not load parent alerts."))
                }
                ParentApiResult(true, formatAlerts(JSONObject(response)))
            }.getOrElse { throwable ->
                ParentApiResult(false, "Alert refresh error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

    fun reviewLatestFlaggedMessageAsSafe(context: Context, onComplete: (Boolean, String) -> Unit) {
        val messageId = latestFlaggedMessageId
        if (messageId == null) {
            onComplete(false, "No flagged message is loaded for review.")
            return
        }
        postJson(
            context = context,
            path = "/api/parent/messages/$messageId/review",
            body = JSONObject().put("reviewed_label", "safe"),
            successMessage = "Latest flagged message marked safe.",
            onComplete = onComplete,
        )
    }

    fun approvePendingLogout(context: Context, onComplete: (Boolean, String) -> Unit) {
        val requestId = pendingLogoutRequestId
        if (requestId == null) {
            onComplete(false, "No pending logout request is loaded.")
            return
        }
        postJson(
            context = context,
            path = "/api/parent/logout-requests/$requestId/approve",
            body = JSONObject(),
            successMessage = "Child logout request approved.",
            onComplete = onComplete,
        )
    }

    fun denyPendingLogout(context: Context, onComplete: (Boolean, String) -> Unit) {
        val requestId = pendingLogoutRequestId
        if (requestId == null) {
            onComplete(false, "No pending logout request is loaded.")
            return
        }
        postJson(
            context = context,
            path = "/api/parent/logout-requests/$requestId/deny",
            body = JSONObject(),
            successMessage = "Child logout request denied.",
            onComplete = onComplete,
        )
    }

    fun createChildDeviceLink(
        context: Context,
        deviceName: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        if (deviceName.isBlank()) {
            onComplete(false, "Enter a child device name first.")
            return
        }
        postJson(
            context = context,
            path = "/api/parent/android-devices",
            body = JSONObject().put("device_name", deviceName),
            successMessage = "Child device link created.",
            onComplete = { ok, message ->
                onComplete(ok, if (ok && latestPairingUri.isNotBlank()) "$message\n\n$latestPairingUri" else message)
            },
            onSuccess = { response ->
                latestPairingUri = response
                    .optJSONObject("instructions")
                    ?.optString("pairing_uri")
                    .orEmpty()
            },
        )
    }

    fun getLatestPairingUri(): String = latestPairingUri

    private fun postJson(
        context: Context,
        path: String,
        body: JSONObject,
        successMessage: String,
        onComplete: (Boolean, String) -> Unit,
        onSuccess: ((JSONObject) -> Unit)? = null,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val cookie = Prefs.getParentSessionCookie(context)
        if (baseUrl.isBlank()) {
            onComplete(false, "Save the backend URL first.")
            return
        }
        if (cookie.isBlank()) {
            onComplete(false, "Sign in as parent first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl$path").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 15000
                    readTimeout = 15000
                    doOutput = true
                    setRequestProperty("Cookie", cookie)
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                }
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body.toString())
                }
                val response = readResponse(connection)
                if (connection.responseCode == 401 || connection.responseCode == 403) {
                    Prefs.clearParentSession(context)
                    return@runCatching ParentApiResult(false, "Parent session expired. Sign in again.")
                }
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Parent action failed."))
                }
                onSuccess?.invoke(JSONObject(response))
                ParentApiResult(true, successMessage)
            }.getOrElse { throwable ->
                ParentApiResult(false, "Parent action error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

    private fun postPublicJson(
        context: Context,
        path: String,
        body: JSONObject,
        successMessage: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            onComplete(false, "Save the backend URL first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl$path").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 15000
                    readTimeout = 15000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                }
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body.toString())
                }
                val response = readResponse(connection)
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Verification action failed."))
                }
                ParentApiResult(true, successMessage)
            }.getOrElse { throwable ->
                ParentApiResult(false, "Verification error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

    private fun readResponse(connection: HttpURLConnection): String {
        val stream = if (connection.responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream ?: connection.inputStream
        }
        return stream.bufferedReader().use { it.readText() }
    }

    private fun parseError(response: String, fallback: String): String =
        runCatching { JSONObject(response).optString("error").ifBlank { fallback } }.getOrDefault(fallback)

    private fun formatAlerts(payload: JSONObject): String {
        latestFlaggedMessageId = null
        pendingLogoutRequestId = null
        val summary = payload.optJSONObject("summary")
        val childName = summary?.optString("child_display_name").orEmpty().ifBlank { "Selected child" }
        val alertCount = summary?.optInt("alert_count", 0) ?: 0
        val highRiskCount = summary?.optInt("high_risk_count", 0) ?: 0
        val deviceCount = summary?.optInt("android_device_count", 0) ?: 0
        val lines = mutableListOf(
            "$childName: $alertCount open alert(s)",
            "$highRiskCount risky message(s) in latest review",
            "$deviceCount linked Android device(s)",
        )

        val messages = payload.optJSONArray("messages")
        var shown = 0
        if (messages != null) {
            for (index in 0 until messages.length()) {
                val message = messages.optJSONObject(index) ?: continue
                val label = message.optString("predicted_label_title").ifBlank { "Flagged" }
                val text = message.optString("message_text").replace(Regex("\\s+"), " ").trim()
                if (message.optString("predicted_label") == "safe" || text.isBlank()) continue
                if (latestFlaggedMessageId == null) {
                    latestFlaggedMessageId = message.optInt("id")
                }
                if (shown == 0) lines += ""
                lines += "$label: ${text.take(90)}"
                shown += 1
                if (shown == 3) break
            }
        }
        if (shown == 0) {
            lines += ""
            lines += "No flagged messages in the latest alert feed."
        }

        val logoutRequests = payload.optJSONArray("logout_requests")
        val pendingLogout = logoutRequests?.optJSONObject(0)
        if (pendingLogout != null) {
            pendingLogoutRequestId = pendingLogout.optInt("id")
            val detail = pendingLogout.optString("detail")
                .ifBlank { pendingLogout.optString("action_description") }
                .ifBlank { "Child requested sign-out." }
            lines += ""
            lines += "Logout request: $detail"
        }
        return lines.joinToString("\n")
    }

    private data class ParentApiResult(val ok: Boolean, val message: String)
}
