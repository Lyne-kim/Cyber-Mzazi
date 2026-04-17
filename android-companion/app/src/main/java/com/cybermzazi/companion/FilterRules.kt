package com.cybermzazi.companion

import android.content.Context

object FilterRules {
    fun normalizePackages(raw: String): List<String> =
        raw.split(",", "\n")
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .distinct()

    fun shouldIngest(context: Context, appPackage: String): Boolean {
        val blocked = normalizePackages(Prefs.getBlockedPackages(context))
        if (appPackage in blocked) return false

        val allowed = normalizePackages(Prefs.getAllowedPackages(context))
        if (allowed.isEmpty()) return true
        return appPackage in allowed
    }
}
