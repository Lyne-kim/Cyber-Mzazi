package com.cybermzazi.companion

import android.content.Context

object Prefs {
    const val ROLE_CHILD = "child"

    private const val PREFS_NAME = "cyber_mzazi_companion"
    private const val KEY_BASE_URL = "base_url"
    private const val KEY_DEVICE_TOKEN = "device_token"
    private const val KEY_DEVICE_NAME = "device_name"
    private const val KEY_LAST_STATUS = "last_status"
    private const val KEY_ALLOWED_PACKAGES = "allowed_packages"
    private const val KEY_BLOCKED_PACKAGES = "blocked_packages"
    private const val KEY_DEVICE_ROLE = "device_role"
    private const val KEY_PARENT_SESSION_COOKIE = "parent_session_cookie"
    private const val KEY_CHILD_SIGNED_IN = "child_signed_in"
    private const val KEY_CHILD_USERNAME = "child_username"
    private const val KEY_CHILD_PARENT_CONTACT = "child_parent_contact"
    private const val KEY_DARK_MODE = "dark_mode"
    private const val KEY_LANGUAGE = "language"
    private const val KEY_IN_APP_SOUNDS = "in_app_sounds"

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

    fun getDeviceRole(context: Context): String =
        prefs(context).getString(KEY_DEVICE_ROLE, ROLE_CHILD).orEmpty().ifBlank { ROLE_CHILD }

    fun isChildRole(context: Context): Boolean = getDeviceRole(context) == ROLE_CHILD

    fun setDeviceRole(context: Context) {
        prefs(context).edit().putString(KEY_DEVICE_ROLE, ROLE_CHILD).apply()
    }

    fun getParentSessionCookie(context: Context): String =
        prefs(context).getString(KEY_PARENT_SESSION_COOKIE, "").orEmpty()

    fun setParentSessionCookie(context: Context, value: String) {
        prefs(context).edit().putString(KEY_PARENT_SESSION_COOKIE, value).apply()
    }

    fun clearParentSession(context: Context) {
        prefs(context).edit().remove(KEY_PARENT_SESSION_COOKIE).apply()
    }

    fun isChildSignedIn(context: Context): Boolean =
        prefs(context).getBoolean(KEY_CHILD_SIGNED_IN, false)

    fun getChildUsername(context: Context): String =
        prefs(context).getString(KEY_CHILD_USERNAME, "").orEmpty()

    fun getChildParentContact(context: Context): String =
        prefs(context).getString(KEY_CHILD_PARENT_CONTACT, "").orEmpty()

    fun setChildSession(context: Context, parentContact: String, childUsername: String) {
        prefs(context).edit()
            .putBoolean(KEY_CHILD_SIGNED_IN, true)
            .putString(KEY_CHILD_PARENT_CONTACT, parentContact)
            .putString(KEY_CHILD_USERNAME, childUsername)
            .apply()
    }

    fun clearChildSession(context: Context) {
        prefs(context).edit()
            .putBoolean(KEY_CHILD_SIGNED_IN, false)
            .remove(KEY_CHILD_PARENT_CONTACT)
            .remove(KEY_CHILD_USERNAME)
            .apply()
    }

    fun isDarkMode(context: Context): Boolean =
        prefs(context).getBoolean(KEY_DARK_MODE, false)

    fun setDarkMode(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_DARK_MODE, value).apply()
    }

    fun getLanguage(context: Context): String =
        prefs(context).getString(KEY_LANGUAGE, "en").orEmpty().ifBlank { "en" }

    fun setLanguage(context: Context, value: String) {
        prefs(context).edit().putString(KEY_LANGUAGE, if (value == "sw") "sw" else "en").apply()
    }

    fun inAppSoundsEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_IN_APP_SOUNDS, true)

    fun setInAppSoundsEnabled(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean(KEY_IN_APP_SOUNDS, value).apply()
    }
}
