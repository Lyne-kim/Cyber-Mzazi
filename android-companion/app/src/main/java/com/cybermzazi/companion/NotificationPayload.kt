package com.cybermzazi.companion

data class NotificationPayload(
    val appName: String,
    val appPackage: String,
    val senderHandle: String?,
    val notificationTitle: String?,
    val notificationText: String,
    val deepLink: String? = null,
)
