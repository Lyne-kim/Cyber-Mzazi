package com.cybermzazi.companion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object NotificationQueueStore {
    private const val KEY_QUEUE = "queued_notifications"
    private const val MAX_QUEUE_SIZE = 50

    private fun prefs(context: Context) =
        context.getSharedPreferences("cyber_mzazi_companion", Context.MODE_PRIVATE)

    fun enqueue(context: Context, payload: NotificationPayload) {
        val queue = getQueue(context).toMutableList()
        queue.add(payload)
        while (queue.size > MAX_QUEUE_SIZE) {
            queue.removeAt(0)
        }
        saveQueue(context, queue)
    }

    fun getQueue(context: Context): List<NotificationPayload> {
        val raw = prefs(context).getString(KEY_QUEUE, "[]").orEmpty()
        val array = JSONArray(raw)
        val items = mutableListOf<NotificationPayload>()
        for (i in 0 until array.length()) {
            val item = array.optJSONObject(i) ?: continue
            items.add(
                NotificationPayload(
                    appName = item.optString("appName"),
                    appPackage = item.optString("appPackage"),
                    senderHandle = item.optString("senderHandle").ifBlank { null },
                    notificationTitle = item.optString("notificationTitle").ifBlank { null },
                    notificationText = item.optString("notificationText"),
                    deepLink = item.optString("deepLink").ifBlank { null },
                ),
            )
        }
        return items
    }

    fun clear(context: Context) {
        prefs(context).edit().putString(KEY_QUEUE, "[]").apply()
    }

    fun replace(context: Context, payloads: List<NotificationPayload>) {
        saveQueue(context, payloads)
    }

    private fun saveQueue(context: Context, payloads: List<NotificationPayload>) {
        val array = JSONArray()
        payloads.forEach { payload ->
            array.put(
                JSONObject().apply {
                    put("appName", payload.appName)
                    put("appPackage", payload.appPackage)
                    put("senderHandle", payload.senderHandle)
                    put("notificationTitle", payload.notificationTitle)
                    put("notificationText", payload.notificationText)
                    put("deepLink", payload.deepLink)
                },
            )
        }
        prefs(context).edit().putString(KEY_QUEUE, array.toString()).apply()
    }
}
