package com.cybermzazi.companion

import android.content.Context
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

object ParentApiClient {
    private const val CONNECT_TIMEOUT_MS = 30000
    private const val READ_TIMEOUT_MS = 90000

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
            onComplete(false, "Pair this device first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/auth/login").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
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
            onSuccessMessage = { response ->
                val details = mutableListOf("Family account created.")
                if (response.optBoolean("requires_email_verification")) {
                    details += if (response.optBoolean("email_verification_sent")) {
                        "Verification email sent."
                    } else {
                        response.optString("email_delivery_message").ifBlank {
                            "Verification email was not sent. Use resend email on the login page."
                        }
                    }
                }
                if (response.optBoolean("requires_phone_verification")) {
                    details += if (response.optBoolean("phone_verification_sent")) {
                        "Phone verification code sent."
                    } else {
                        response.optString("phone_delivery_message").ifBlank {
                            "Phone verification code was not sent. Use resend code on the login page."
                        }
                    }
                }
                details += "Verify before signing in."
                details.joinToString("\n")
            },
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
            onComplete(false, "Pair this device first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/auth/login").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
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
                val cookie = connection.headerFields["Set-Cookie"]
                    ?.firstOrNull()
                    ?.substringBefore(";")
                    .orEmpty()
                if (cookie.isBlank()) {
                    return@runCatching ParentApiResult(false, "Child sign-in did not return a session.")
                }
                Prefs.setParentSessionCookie(context, cookie)
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
        fetchDashboard(context) { ok, dashboard, message ->
            onComplete(ok, dashboard?.summaryText ?: message)
        }
    }

    fun fetchDashboard(context: Context, onComplete: (Boolean, ParentDashboardData?, String) -> Unit) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val cookie = Prefs.getParentSessionCookie(context)
        if (baseUrl.isBlank()) {
            onComplete(false, null, "App connection is not ready. Pair the device again.")
            return
        }
        if (cookie.isBlank()) {
            onComplete(false, null, "Sign in as parent to load dashboard.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/parent/dashboard").openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
                    setRequestProperty("Cookie", cookie)
                    setRequestProperty("Accept", "application/json")
                }
                val response = readResponse(connection)
                if (connection.responseCode == 401 || connection.responseCode == 403) {
                    Prefs.clearParentSession(context)
                    return@runCatching ParentDashboardResult(false, null, "Parent session expired. Sign in again.")
                }
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentDashboardResult(false, null, parseError(response, "Could not load parent dashboard."))
                }
                val dashboard = parseDashboard(JSONObject(response))
                ParentDashboardResult(true, dashboard, dashboard.summaryText)
            }.getOrElse { throwable ->
                ParentDashboardResult(false, null, "Dashboard refresh error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.dashboard, result.message)
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

    fun logout(context: Context, onComplete: (Boolean, String) -> Unit) {
        postJson(
            context = context,
            path = "/api/auth/logout",
            body = JSONObject(),
            successMessage = "Signed out.",
            onComplete = onComplete,
        )
    }

    fun updateProfile(
        context: Context,
        name: String,
        contact: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postJson(
            context = context,
            path = "/api/account/profile",
            body = JSONObject()
                .put("name", name)
                .put("contact", contact),
            successMessage = "Profile saved.",
            onComplete = onComplete,
        )
    }

    fun changePassword(
        context: Context,
        currentPassword: String,
        newPassword: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postJson(
            context = context,
            path = "/api/account/change-password",
            body = JSONObject()
                .put("current_password", currentPassword)
                .put("new_password", newPassword),
            successMessage = "Password changed.",
            onComplete = onComplete,
        )
    }

    fun sendPasswordVerification(
        context: Context,
        channel: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postJson(
            context = context,
            path = "/api/account/password-verification/send",
            body = JSONObject().put("channel", channel),
            successMessage = "Password verification code sent.",
            onComplete = onComplete,
        )
    }

    fun confirmPasswordVerification(
        context: Context,
        code: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        postJson(
            context = context,
            path = "/api/account/password-verification/confirm",
            body = JSONObject().put("code", code),
            successMessage = "Password change verified.",
            onComplete = onComplete,
        )
    }

    fun requestChildLogout(context: Context, onComplete: (Boolean, String) -> Unit) {
        postJson(
            context = context,
            path = "/api/child/logout-request",
            body = JSONObject(),
            successMessage = "Logout request sent to parent.",
            onComplete = onComplete,
        )
    }

    fun setLanguage(context: Context, language: String, onComplete: (Boolean, String) -> Unit) {
        postJson(
            context = context,
            path = "/api/ui/language",
            body = JSONObject().put("language", language),
            successMessage = "Language saved.",
            onComplete = onComplete,
        )
    }

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
            onComplete(false, "Pair this device first.")
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
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
                    doOutput = true
                    setRequestProperty("Cookie", cookie)
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                }
                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body.toString())
                }
                val response = readResponse(connection)
                if (connection.responseCode == 401) {
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
        onSuccessMessage: ((JSONObject) -> String)? = null,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            onComplete(false, "Pair this device first.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl$path").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
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
                val responseJson = JSONObject(response.ifBlank { "{}" })
                ParentApiResult(true, onSuccessMessage?.invoke(responseJson) ?: successMessage)
            }.getOrElse { throwable ->
                ParentApiResult(
                    false,
                    "Verification error: ${throwable.message ?: "Unknown error"}. Check your internet connection and try again.",
                )
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

    private fun parseDashboard(payload: JSONObject): ParentDashboardData {
        latestFlaggedMessageId = null
        pendingLogoutRequestId = null
        val family = payload.optJSONObject("family")
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
        val latestDevice = payload.optJSONArray("linked_devices")?.optJSONObject(0)
        val deviceStatus = if (latestDevice != null) {
            val deviceName = latestDevice.optString("device_name").ifBlank { childName }
            "Device paired\n$deviceName"
        } else {
            "No child device paired yet."
        }
        return ParentDashboardData(
            parentName = payload.optJSONObject("selected_child")?.optString("parent_name").orEmpty(),
            familyName = family?.optString("family_name").orEmpty().ifBlank { "Your family" },
            childName = childName,
            alertCount = alertCount,
            recentMessages = lines.drop(3).joinToString("\n").trim().ifBlank { "No risky messages yet." },
            deviceStatus = deviceStatus,
            summaryText = lines.joinToString("\n"),
        )
    }

    private data class ParentApiResult(val ok: Boolean, val message: String)
    private data class ParentDashboardResult(
        val ok: Boolean,
        val dashboard: ParentDashboardData?,
        val message: String,
    )

    data class ParentDashboardData(
        val parentName: String,
        val familyName: String,
        val childName: String,
        val alertCount: Int,
        val recentMessages: String,
        val deviceStatus: String,
        val summaryText: String,
    )
}
