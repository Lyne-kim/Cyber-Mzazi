package com.cybermzazi.companion

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class CyberMzaziNotificationListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        if (!Prefs.isChildRole(applicationContext)) return
        if (sbn.packageName == packageName) return
        if (sbn.notification.flags and Notification.FLAG_ONGOING_EVENT != 0) return
        if (!FilterRules.shouldIngest(applicationContext, sbn.packageName)) return

        val extras = sbn.notification.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim()
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()?.trim()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.trim()
        val lines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)
            ?.joinToString("\n") { it.toString() }
            ?.trim()
        val body = listOfNotNull(bigText, text, lines).firstOrNull { !it.isNullOrBlank() } ?: return

        val appName = runCatching {
            packageManager.getApplicationLabel(
                packageManager.getApplicationInfo(sbn.packageName, 0),
            ).toString()
        }.getOrDefault(sbn.packageName)

        val payload = NotificationPayload(
            appName = appName,
            appPackage = sbn.packageName,
            senderHandle = title,
            notificationTitle = title,
            notificationText = body,
            deepLink = null,
        )
        RecentNotificationLog.append(
            applicationContext,
            appName,
            title,
            body,
            "Captured from notification listener",
        )
        IngestionClient.sendNotification(applicationContext, payload)
    }
}
