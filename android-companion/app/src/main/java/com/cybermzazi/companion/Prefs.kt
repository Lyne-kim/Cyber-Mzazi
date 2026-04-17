package com.cybermzazi.companion

import android.content.Context

object Prefs {
    private const val PREFS_NAME = "cyber_mzazi_companion"
    private const val KEY_BASE_URL = "base_url"
    private const val KEY_DEVICE_TOKEN = "device_token"
    private const val KEY_DEVICE_NAME = "device_name"
    private const val KEY_LAST_STATUS = "last_status"
    private const val KEY_ALLOWED_PACKAGES = "allowed_packages"
    private const val KEY_BLOCKED_PACKAGES = "blocked_packages"

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getBaseUrl(context: Context): String =
        prefs(context).getString(KEY_BASE_URL, "https://cyber-mzazi.onrender.com").orEmpty()

    fun setBaseUrl(context: Context, value: String) {
        prefs(context).edit().putString(KEY_BASE_URL, value).apply()
    }

    fun getDeviceToken(context: Context): String =
        prefs(context).getString(KEY_DEVICE_TOKEN, "").orEmpty()

    fun setDeviceToken(context: Context, value: String) {
        prefs(context).edit().putString(KEY_DEVICE_TOKEN, value).apply()
    }

    fun getDeviceName(context: Context): String =
        prefs(context).getString(KEY_DEVICE_NAME, "").orEmpty()

    fun setDeviceName(context: Context, value: String) {
        prefs(context).edit().putString(KEY_DEVICE_NAME, value).apply()
    }

    fun getLastStatus(context: Context): String =
        prefs(context).getString(KEY_LAST_STATUS, "No uploads yet.").orEmpty()

    fun setLastStatus(context: Context, value: String) {
        prefs(context).edit().putString(KEY_LAST_STATUS, value).apply()
    }

    fun getAllowedPackages(context: Context): String =
        prefs(context).getString(KEY_ALLOWED_PACKAGES, "").orEmpty()

    fun setAllowedPackages(context: Context, value: String) {
        prefs(context).edit().putString(KEY_ALLOWED_PACKAGES, value).apply()
    }

    fun getBlockedPackages(context: Context): String =
        prefs(context).getString(KEY_BLOCKED_PACKAGES, "").orEmpty()

    fun setBlockedPackages(context: Context, value: String) {
        prefs(context).edit().putString(KEY_BLOCKED_PACKAGES, value).apply()
    }
}
