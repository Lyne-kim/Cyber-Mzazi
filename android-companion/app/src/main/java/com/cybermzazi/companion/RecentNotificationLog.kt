package com.cybermzazi.companion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object RecentNotificationLog {
    private const val KEY_LOG = "recent_notification_log"
    private const val MAX_ITEMS = 12

    private fun prefs(context: Context) =
        context.getSharedPreferences("cyber_mzazi_companion", Context.MODE_PRIVATE)

    fun append(
        context: Context,
        appName: String,
        title: String?,
        body: String,
        status: String,
    ) {
        val entries = getEntries(context).toMutableList()
        val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
        entries.add(
            mapOf(
                "timestamp" to timestamp,
                "appName" to appName,
                "title" to (title ?: ""),
                "body" to body.take(140),
                "status" to status,
            ),
        )
        while (entries.size > MAX_ITEMS) {
            entries.removeAt(0)
        }
        saveEntries(context, entries)
    }

    fun render(context: Context): String {
        val entries = getEntries(context)
        if (entries.isEmpty()) return "No captured notifications yet."
        return entries.asReversed().joinToString("\n\n") { item ->
            buildString {
                append(item["timestamp"])
                append(" - ")
                append(item["appName"])
                if (!item["title"].isNullOrBlank()) {
                    append(" / ")
                    append(item["title"])
                }
                append("\n")
                append(item["status"])
                append("\n")
                append(item["body"])
            }
        }
    }

    private fun getEntries(context: Context): List<Map<String, String>> {
        val raw = prefs(context).getString(KEY_LOG, "[]").orEmpty()
        val array = JSONArray(raw)
        val items = mutableListOf<Map<String, String>>()
        for (i in 0 until array.length()) {
            val item = array.optJSONObject(i) ?: continue
            items.add(
                mapOf(
                    "timestamp" to item.optString("timestamp"),
                    "appName" to item.optString("appName"),
                    "title" to item.optString("title"),
                    "body" to item.optString("body"),
                    "status" to item.optString("status"),
                ),
            )
        }
        return items
    }

    private fun saveEntries(context: Context, entries: List<Map<String, String>>) {
        val array = JSONArray()
        entries.forEach { entry ->
            array.put(
                JSONObject().apply {
                    put("timestamp", entry["timestamp"])
                    put("appName", entry["appName"])
                    put("title", entry["title"])
                    put("body", entry["body"])
                    put("status", entry["status"])
                },
            )
        }
        prefs(context).edit().putString(KEY_LOG, array.toString()).apply()
    }
}
