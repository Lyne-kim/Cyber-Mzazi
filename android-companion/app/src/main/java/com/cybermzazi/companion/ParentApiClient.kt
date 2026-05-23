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
                val cookie = storeSessionCookie(context, connection)
                if (cookie.isBlank()) {
                    return@runCatching ParentApiResult(false, "Child sign-in did not return a session.")
                }
                ParentApiResult(true, "Child sign-in ready.")
            }.getOrElse { throwable ->
                ParentApiResult(false, "Child sign-in error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

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
        onComplete: (Boolean, String) -> Unit,
    ) {
        postJson(
            context = context,
            path = "/api/account/profile",
            body = JSONObject().put("name", name),
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

    fun fetchChildLogoutStatus(context: Context, onComplete: (Boolean, String?, String) -> Unit) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val cookie = Prefs.getParentSessionCookie(context)
        if (baseUrl.isBlank() || cookie.isBlank()) {
            onComplete(false, null, "Child session is not ready.")
            return
        }
        executor.execute {
            val result = runCatching {
                val connection = (URL("$baseUrl/api/child/home").openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
                    setRequestProperty("Cookie", cookie)
                    setRequestProperty("Accept", "application/json")
                }
                val response = readResponse(connection)
                if (connection.responseCode !in 200..299) {
                    ChildLogoutStatusResult(false, null, parseError(response, "Could not check logout approval."))
                } else {
                    val pendingLogout = JSONObject(response).optJSONObject("pending_logout")
                    ChildLogoutStatusResult(true, pendingLogout?.optString("status")?.ifBlank { null }, "Logout status checked.")
                }
            }.getOrElse { throwable ->
                ChildLogoutStatusResult(false, null, "Logout status error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.status, result.message)
        }
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

    fun askAssistant(context: Context, prompt: String, onComplete: (Boolean, String) -> Unit) {
        val trimmedPrompt = prompt.trim()
        if (trimmedPrompt.isBlank()) {
            onComplete(false, "Enter a message or question first.")
            return
        }

        postJsonForResponse(
            context = context,
            path = "/api/assistant/chat",
            body = JSONObject().put("prompt", trimmedPrompt),
        ) { ok, responseOrError ->
            if (!ok) {
                onComplete(false, responseOrError)
                return@postJsonForResponse
            }
            val formatted = runCatching {
                val root = JSONObject(responseOrError)
                val assistant = root.getJSONObject("assistant")
                val title = assistant.optString("label_title", "Safety check")
                val risk = assistant.optString("risk_level", "unknown").replaceFirstChar { it.uppercase() }
                val confidence = (assistant.optDouble("confidence", 0.0) * 100).toInt()
                val assistantMessage = assistant.optString("assistant_message")
                val explanation = assistant.optString("explanation")
                val guidance = assistant.optString("guidance")
                val nextSteps = assistant.optJSONArray("next_steps")
                buildString {
                    if (assistantMessage.isNotBlank()) {
                        append(assistantMessage)
                    } else if (explanation.isNotBlank()) {
                        append(explanation)
                    } else {
                        append("I checked this and can help you decide what to do next.")
                    }
                    append("\n\nSafety signal: ").append(title)
                    if (risk.lowercase() != "none") append(" / ").append(risk).append(" risk")
                    if (confidence > 0) append(" (").append(confidence).append("%)")
                    if (guidance.isNotBlank()) append("\n\nWhat to do:\n").append(guidance)
                    if (nextSteps != null && nextSteps.length() > 0) {
                        append("\n\nNext steps:")
                        for (index in 0 until nextSteps.length()) {
                            append("\n").append(index + 1).append(". ").append(nextSteps.optString(index))
                        }
                    }
                    if (root.optBoolean("guardian_alerted", false) || assistant.optBoolean("should_alert_guardian", false)) {
                        append("\n\nI shared this with your parent or guardian so they can help.")
                    }
                }
            }.getOrElse {
                "Assistant answered, but the response could not be displayed clearly."
            }
            onComplete(true, formatted)
        }
    }

    private fun postJson(
        context: Context,
        path: String,
        body: JSONObject,
        successMessage: String,
        onComplete: (Boolean, String) -> Unit,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val cookie = Prefs.getParentSessionCookie(context)
        if (baseUrl.isBlank()) {
            onComplete(false, "Pair this device first.")
            return
        }
        if (cookie.isBlank()) {
            onComplete(false, "Sign in first.")
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
                storeSessionCookie(context, connection)
                if (connection.responseCode == 401) {
                    Prefs.clearParentSession(context)
                    return@runCatching ParentApiResult(false, "Session expired. Sign in again.")
                }
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Action failed."))
                }
                ParentApiResult(true, successMessage)
            }.getOrElse { throwable ->
                ParentApiResult(false, "Action error: ${throwable.message ?: "Unknown error"}")
            }
            onComplete(result.ok, result.message)
        }
    }

    private fun postJsonForResponse(
        context: Context,
        path: String,
        body: JSONObject,
        onComplete: (Boolean, String) -> Unit,
    ) {
        val baseUrl = Prefs.getBaseUrl(context).trim().trimEnd('/')
        val cookie = Prefs.getParentSessionCookie(context)
        if (baseUrl.isBlank()) {
            onComplete(false, "Pair this device first.")
            return
        }
        if (cookie.isBlank()) {
            onComplete(false, "Sign in first.")
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
                storeSessionCookie(context, connection)
                if (connection.responseCode == 401) {
                    Prefs.clearParentSession(context)
                    return@runCatching ParentApiResult(false, "Session expired. Sign in again.")
                }
                if (connection.responseCode !in 200..299) {
                    return@runCatching ParentApiResult(false, parseError(response, "Assistant request failed."))
                }
                ParentApiResult(true, response)
            }.getOrElse { throwable ->
                ParentApiResult(false, "Assistant error: ${throwable.message ?: "Unknown error"}")
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

    private fun storeSessionCookie(context: Context, connection: HttpURLConnection): String {
        val cookie = connection.headerFields["Set-Cookie"]
            ?.firstOrNull()
            ?.substringBefore(";")
            .orEmpty()
        if (cookie.isNotBlank()) {
            Prefs.setParentSessionCookie(context, cookie)
        }
        return cookie
    }

    private data class ParentApiResult(val ok: Boolean, val message: String)

    private data class ChildLogoutStatusResult(
        val ok: Boolean,
        val status: String?,
        val message: String,
    )
}
