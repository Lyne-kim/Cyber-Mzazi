package com.cybermzazi.companion

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import androidx.core.content.ContextCompat
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import com.google.zxing.BarcodeFormat
import com.journeyapps.barcodescanner.BarcodeEncoder
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

class MainActivity : AppCompatActivity() {

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var backButton: TextView
    private lateinit var menuToggle: TextView
    private lateinit var roleBadge: TextView
    private lateinit var roleSummaryText: TextView
    private lateinit var captureRoleHint: TextView
    private lateinit var parentRoleButton: Button
    private lateinit var childRoleButton: Button
    private lateinit var baseUrlInput: EditText
    private lateinit var tokenInput: EditText
    private lateinit var deviceNameInput: EditText
    private lateinit var parentIdentifierInput: EditText
    private lateinit var parentPasswordInput: EditText
    private lateinit var parentPhoneCodeInput: EditText
    private lateinit var parentChildDeviceNameInput: EditText
    private lateinit var parentAlertSummaryText: TextView
    private lateinit var parentCaptureStatusText: TextView
    private lateinit var childSetupStatusText: TextView
    private lateinit var parentGreetingText: TextView
    private lateinit var parentFamilyNameText: TextView
    private lateinit var parentChildStatusText: TextView
    private lateinit var parentAlertsWeekText: TextView
    private lateinit var parentRecentMessagesText: TextView
    private lateinit var parentDeviceStatusText: TextView
    private lateinit var childGreetingText: TextView
    private lateinit var registerFamilyNameInput: EditText
    private lateinit var registerParentNameInput: EditText
    private lateinit var registerParentContactInput: EditText
    private lateinit var registerParentPasswordInput: EditText
    private lateinit var registerChildNameInput: EditText
    private lateinit var registerChildUsernameInput: EditText
    private lateinit var registerChildPasswordInput: EditText
    private lateinit var registerFamilyStatusText: TextView
    private lateinit var childParentContactInput: EditText
    private lateinit var childUsernameInput: EditText
    private lateinit var childPasswordInput: EditText
    private lateinit var childLoginStatusText: TextView
    private lateinit var allowedPackagesInput: EditText
    private lateinit var blockedPackagesInput: EditText
    private lateinit var statusText: TextView
    private lateinit var recentLogText: TextView
    private lateinit var pairingQrImage: ImageView
    private lateinit var pairingLinkText: TextView
    private lateinit var darkModeSwitch: Switch
    private lateinit var languageSwitch: Switch
    private lateinit var inAppSoundsSwitch: Switch
    private lateinit var profileNameInput: EditText
    private lateinit var profileContactInput: EditText
    private lateinit var passwordVerificationCodeInput: EditText
    private lateinit var currentPasswordInput: EditText
    private lateinit var newPasswordInput: EditText
    private lateinit var confirmNewPasswordInput: EditText

    private lateinit var menuHome: TextView
    private lateinit var menuAuth: TextView
    private lateinit var menuQr: TextView
    private lateinit var menuSettings: TextView
    private lateinit var menuCapture: TextView
    private lateinit var menuFilters: TextView
    private lateinit var menuStatus: TextView
    private lateinit var menuLog: TextView
    private lateinit var menuProfile: TextView
    private lateinit var menuPassword: TextView
    private lateinit var menuLogout: TextView

    private lateinit var roleSection: View
    private lateinit var qrSection: View
    private lateinit var settingsSection: View
    private lateinit var actionsSection: View
    private lateinit var filtersSection: View
    private lateinit var statusSection: View
    private lateinit var logSection: View
    private lateinit var parentHomeSection: View
    private lateinit var parentDashboardSection: View
    private lateinit var childHomeSection: View
    private lateinit var registerFamilySection: View
    private lateinit var childLoginSection: View
    private lateinit var profileSection: View
    private lateinit var passwordSection: View

    private lateinit var openChildLoginButton: Button
    private lateinit var registerFamilyButton: Button
    private lateinit var childLoginButton: Button
    private lateinit var openParentDashboardButton: Button
    private lateinit var openParentAlertsButton: Button
    private lateinit var openChildDevicesButton: Button
    private lateinit var parentLoginButton: Button
    private lateinit var parentVerifyPhoneButton: Button
    private lateinit var parentResendPhoneCodeButton: Button
    private lateinit var refreshParentAlertsButton: Button
    private lateinit var openParentNotificationSettingsButton: Button
    private lateinit var reviewLatestSafeButton: Button
    private lateinit var approveLogoutButton: Button
    private lateinit var denyLogoutButton: Button
    private lateinit var createChildDeviceLinkButton: Button
    private lateinit var copyPairingLinkButton: Button
    private lateinit var sharePairingLinkButton: Button
    private lateinit var goPairChildButton: Button
    private lateinit var goCaptureChildButton: Button
    private lateinit var goFiltersChildButton: Button
    private lateinit var saveButton: Button
    private lateinit var scanQrButton: Button
    private lateinit var passwordConfirmCodeButton: Button

    private var currentSection = 0
    private var isPopulatingFields = false
    private var childSignedIn = false

    private val scanLauncher = registerForActivityResult(ScanContract()) { result ->
        val contents = result.contents ?: return@registerForActivityResult
        applyPairingPayload(contents)
    }

    private val cameraPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                launchQrScanner()
            } else {
                Toast.makeText(this, R.string.camera_permission_required, Toast.LENGTH_SHORT).show()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppCompatDelegate.setDefaultNightMode(
            if (Prefs.isDarkMode(this)) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO,
        )
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(Prefs.getLanguage(this)))
        setContentView(R.layout.activity_main)

        drawerLayout = findViewById(R.id.drawerLayout)
        backButton = findViewById(R.id.backButton)
        menuToggle = findViewById(R.id.menuToggle)
        roleBadge = findViewById(R.id.roleBadge)
        roleSummaryText = findViewById(R.id.roleSummaryText)
        captureRoleHint = findViewById(R.id.captureRoleHint)
        parentRoleButton = findViewById(R.id.parentRoleButton)
        childRoleButton = findViewById(R.id.childRoleButton)
        baseUrlInput = findViewById(R.id.baseUrlInput)
        tokenInput = findViewById(R.id.tokenInput)
        deviceNameInput = findViewById(R.id.deviceNameInput)
        parentIdentifierInput = findViewById(R.id.parentIdentifierInput)
        parentPasswordInput = findViewById(R.id.parentPasswordInput)
        parentPhoneCodeInput = findViewById(R.id.parentPhoneCodeInput)
        parentChildDeviceNameInput = findViewById(R.id.parentChildDeviceNameInput)
        parentAlertSummaryText = findViewById(R.id.parentAlertSummaryText)
        parentCaptureStatusText = findViewById(R.id.parentCaptureStatusText)
        childSetupStatusText = findViewById(R.id.childSetupStatusText)
        parentGreetingText = findViewById(R.id.parentGreetingText)
        parentFamilyNameText = findViewById(R.id.parentFamilyNameText)
        parentChildStatusText = findViewById(R.id.parentChildStatusText)
        parentAlertsWeekText = findViewById(R.id.parentAlertsWeekText)
        parentRecentMessagesText = findViewById(R.id.parentRecentMessagesText)
        parentDeviceStatusText = findViewById(R.id.parentDeviceStatusText)
        childGreetingText = findViewById(R.id.childGreetingText)
        registerFamilyNameInput = findViewById(R.id.registerFamilyNameInput)
        registerParentNameInput = findViewById(R.id.registerParentNameInput)
        registerParentContactInput = findViewById(R.id.registerParentContactInput)
        registerParentPasswordInput = findViewById(R.id.registerParentPasswordInput)
        registerChildNameInput = findViewById(R.id.registerChildNameInput)
        registerChildUsernameInput = findViewById(R.id.registerChildUsernameInput)
        registerChildPasswordInput = findViewById(R.id.registerChildPasswordInput)
        registerFamilyStatusText = findViewById(R.id.registerFamilyStatusText)
        childParentContactInput = findViewById(R.id.childParentContactInput)
        childUsernameInput = findViewById(R.id.childUsernameInput)
        childPasswordInput = findViewById(R.id.childPasswordInput)
        childLoginStatusText = findViewById(R.id.childLoginStatusText)
        allowedPackagesInput = findViewById(R.id.allowedPackagesInput)
        blockedPackagesInput = findViewById(R.id.blockedPackagesInput)
        statusText = findViewById(R.id.statusText)
        recentLogText = findViewById(R.id.recentLogText)
        pairingQrImage = findViewById(R.id.pairingQrImage)
        pairingLinkText = findViewById(R.id.pairingLinkText)
        darkModeSwitch = findViewById(R.id.darkModeSwitch)
        languageSwitch = findViewById(R.id.languageSwitch)
        inAppSoundsSwitch = findViewById(R.id.inAppSoundsSwitch)
        profileNameInput = findViewById(R.id.profileNameInput)
        profileContactInput = findViewById(R.id.profileContactInput)
        passwordVerificationCodeInput = findViewById(R.id.passwordVerificationCodeInput)
        currentPasswordInput = findViewById(R.id.currentPasswordInput)
        newPasswordInput = findViewById(R.id.newPasswordInput)
        confirmNewPasswordInput = findViewById(R.id.confirmNewPasswordInput)

        menuHome = findViewById(R.id.menuHome)
        menuAuth = findViewById(R.id.menuAuth)
        menuQr = findViewById(R.id.menuQr)
        menuSettings = findViewById(R.id.menuSettings)
        menuCapture = findViewById(R.id.menuCapture)
        menuFilters = findViewById(R.id.menuFilters)
        menuStatus = findViewById(R.id.menuStatus)
        menuLog = findViewById(R.id.menuLog)
        menuProfile = findViewById(R.id.menuProfile)
        menuPassword = findViewById(R.id.menuPassword)
        menuLogout = findViewById(R.id.menuLogout)

        roleSection = findViewById(R.id.roleSection)
        qrSection = findViewById(R.id.qrSection)
        settingsSection = findViewById(R.id.settingsSection)
        actionsSection = findViewById(R.id.actionsSection)
        filtersSection = findViewById(R.id.filtersSection)
        statusSection = findViewById(R.id.statusSection)
        logSection = findViewById(R.id.logSection)
        parentHomeSection = findViewById(R.id.parentHomeSection)
        parentDashboardSection = findViewById(R.id.parentDashboardSection)
        childHomeSection = findViewById(R.id.childHomeSection)
        registerFamilySection = findViewById(R.id.registerFamilySection)
        childLoginSection = findViewById(R.id.childLoginSection)
        profileSection = findViewById(R.id.profileSection)
        passwordSection = findViewById(R.id.passwordSection)
        openChildLoginButton = findViewById(R.id.openChildLoginButton)
        registerFamilyButton = findViewById(R.id.registerFamilyButton)
        childLoginButton = findViewById(R.id.childLoginButton)
        openParentDashboardButton = findViewById(R.id.openParentDashboardButton)
        openParentAlertsButton = findViewById(R.id.openParentAlertsButton)
        openChildDevicesButton = findViewById(R.id.openChildDevicesButton)
        parentLoginButton = findViewById(R.id.parentLoginButton)
        parentVerifyPhoneButton = findViewById(R.id.parentVerifyPhoneButton)
        parentResendPhoneCodeButton = findViewById(R.id.parentResendPhoneCodeButton)
        refreshParentAlertsButton = findViewById(R.id.refreshParentAlertsButton)
        openParentNotificationSettingsButton = findViewById(R.id.openParentNotificationSettingsButton)
        reviewLatestSafeButton = findViewById(R.id.reviewLatestSafeButton)
        approveLogoutButton = findViewById(R.id.approveLogoutButton)
        denyLogoutButton = findViewById(R.id.denyLogoutButton)
        createChildDeviceLinkButton = findViewById(R.id.createChildDeviceLinkButton)
        copyPairingLinkButton = findViewById(R.id.copyPairingLinkButton)
        sharePairingLinkButton = findViewById(R.id.sharePairingLinkButton)
        goPairChildButton = findViewById(R.id.goPairChildButton)
        goCaptureChildButton = findViewById(R.id.goCaptureChildButton)
        goFiltersChildButton = findViewById(R.id.goFiltersChildButton)
        saveButton = findViewById(R.id.saveButton)
        scanQrButton = findViewById(R.id.scanQrButton)
        passwordConfirmCodeButton = findViewById(R.id.passwordConfirmCodeButton)

        backButton.setOnClickListener { navigateBack() }
        menuToggle.setOnClickListener {
            if (!isSignedIn()) return@setOnClickListener
            if (drawerLayout.isDrawerOpen(GravityCompat.START)) {
                drawerLayout.closeDrawer(GravityCompat.START)
            } else {
                drawerLayout.openDrawer(GravityCompat.START)
            }
        }

        menuHome.setOnClickListener {
            when {
                childSignedIn -> showSection(SECTION_CHILD_ACCOUNT)
                else -> showSection(SECTION_HOME)
            }
        }
        menuAuth.setOnClickListener { showSection(SECTION_CHILD_AUTH) }
        menuQr.setOnClickListener { showSection(SECTION_QR) }
        menuSettings.setOnClickListener { showSection(SECTION_SETTINGS) }
        menuCapture.setOnClickListener { showSection(SECTION_CAPTURE) }
        menuFilters.setOnClickListener { showSection(SECTION_FILTERS) }
        menuStatus.setOnClickListener { showSection(SECTION_STATUS) }
        menuLog.setOnClickListener { showSection(SECTION_LOGS) }
        menuProfile.setOnClickListener { showSection(SECTION_PROFILE) }
        menuPassword.setOnClickListener { showSection(SECTION_PASSWORD) }
        menuLogout.setOnClickListener { signOut() }
        openChildLoginButton.setOnClickListener { showSection(SECTION_CHILD_AUTH) }
        findViewById<Button>(R.id.registerBackToLoginButton).setOnClickListener {
            showSection(SECTION_CHILD_AUTH)
        }
        parentRoleButton.setOnClickListener { setDeviceRole(Prefs.ROLE_CHILD) }
        childRoleButton.setOnClickListener { setDeviceRole(Prefs.ROLE_CHILD) }

        openParentDashboardButton.setOnClickListener { showSection(SECTION_CHILD_ACCOUNT) }
        findViewById<Button>(R.id.parentDashboardPairButton).setOnClickListener { showSection(SECTION_QR) }
        findViewById<Button>(R.id.parentDashboardSettingsButton).setOnClickListener { showSection(SECTION_SETTINGS) }
        openParentAlertsButton.setOnClickListener { openWebPath("/parent/alerts") }
        openChildDevicesButton.setOnClickListener { openWebPath("/parent/child-profile") }
        parentLoginButton.setOnClickListener { signInParent() }
        registerFamilyButton.setOnClickListener { registerFamilyAccount() }
        childLoginButton.setOnClickListener { signInChild() }
        parentVerifyPhoneButton.setOnClickListener { verifyParentPhone() }
        parentResendPhoneCodeButton.setOnClickListener { resendParentPhoneCode() }
        refreshParentAlertsButton.setOnClickListener { refreshParentAlerts() }
        openParentNotificationSettingsButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        reviewLatestSafeButton.setOnClickListener {
            runParentAction { callback ->
                ParentApiClient.reviewLatestFlaggedMessageAsSafe(this, callback)
            }
        }
        approveLogoutButton.setOnClickListener {
            runParentAction { callback ->
                ParentApiClient.approvePendingLogout(this, callback)
            }
        }
        denyLogoutButton.setOnClickListener {
            runParentAction { callback ->
                ParentApiClient.denyPendingLogout(this, callback)
            }
        }
        createChildDeviceLinkButton.setOnClickListener { createChildDeviceLink() }
        copyPairingLinkButton.setOnClickListener { copyLatestPairingLink() }
        sharePairingLinkButton.setOnClickListener { shareLatestPairingLink() }
        goPairChildButton.setOnClickListener { signOut() }
        goCaptureChildButton.setOnClickListener { showSection(SECTION_CAPTURE) }
        goFiltersChildButton.setOnClickListener { showSection(SECTION_SETTINGS) }

        saveButton.setOnClickListener { saveSettings() }
        scanQrButton.setOnClickListener { startQrPairing() }
        findViewById<Button>(R.id.notificationAccessButton).setOnClickListener {
            if (!Prefs.isChildRole(this)) {
                Toast.makeText(this, R.string.parent_mode_capture_disabled, Toast.LENGTH_SHORT).show()
            } else {
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            }
        }
        findViewById<Button>(R.id.sendTestButton).setOnClickListener {
            if (!Prefs.isChildRole(this)) {
                Toast.makeText(this, R.string.parent_mode_capture_disabled, Toast.LENGTH_SHORT).show()
            } else {
                sendTestPayload()
            }
        }
        findViewById<Button>(R.id.retryQueueButton).setOnClickListener {
            if (!Prefs.isChildRole(this)) {
                Toast.makeText(this, R.string.parent_mode_capture_disabled, Toast.LENGTH_SHORT).show()
            } else {
                retryQueue()
            }
        }
        findViewById<Button>(R.id.editProfileButton).setOnClickListener {
            showSection(SECTION_PROFILE)
        }
        findViewById<Button>(R.id.changePasswordButton).setOnClickListener {
            showSection(SECTION_PASSWORD)
        }
        findViewById<Button>(R.id.signOutButton).setOnClickListener { signOut() }
        findViewById<Button>(R.id.profileSaveButton).setOnClickListener {
            saveProfile()
        }
        findViewById<Button>(R.id.passwordVerifyButton).setOnClickListener { sendPasswordVerificationCode() }
        passwordConfirmCodeButton.setOnClickListener { confirmPasswordVerificationCode() }
        findViewById<Button>(R.id.passwordSaveButton).setOnClickListener {
            changePassword()
        }

        darkModeSwitch.setOnCheckedChangeListener { _, enabled ->
            if (isPopulatingFields) return@setOnCheckedChangeListener
            if (Prefs.isDarkMode(this) == enabled) return@setOnCheckedChangeListener
            Prefs.setDarkMode(this, enabled)
            AppCompatDelegate.setDefaultNightMode(
                if (enabled) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO,
            )
        }
        languageSwitch.setOnCheckedChangeListener { _, enabled ->
            if (isPopulatingFields) return@setOnCheckedChangeListener
            val language = if (enabled) "sw" else "en"
            if (Prefs.getLanguage(this) == language) return@setOnCheckedChangeListener
            Prefs.setLanguage(this, language)
            AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(language))
            if (isSignedIn()) {
                ParentApiClient.setLanguage(this, language) { _, message ->
                    runOnUiThread { Toast.makeText(this, message, Toast.LENGTH_SHORT).show() }
                }
            } else {
                Toast.makeText(this, if (enabled) R.string.language_sw_saved else R.string.language_en_saved, Toast.LENGTH_SHORT).show()
            }
        }
        inAppSoundsSwitch.setOnCheckedChangeListener { _, enabled ->
            if (isPopulatingFields) return@setOnCheckedChangeListener
            Prefs.setInAppSoundsEnabled(this, enabled)
            Toast.makeText(this, if (enabled) R.string.sounds_on else R.string.sounds_off, Toast.LENGTH_SHORT).show()
        }

        registerSettingsDirtyWatchers()
        Prefs.setDeviceRole(this, Prefs.ROLE_CHILD)
        childSignedIn = Prefs.isChildSignedIn(this)
        populateFields()
        restoreChildSessionUi()
        updateRoleUi()
        val restoredSection = savedInstanceState?.getInt(STATE_CURRENT_SECTION)
            ?: if (childSignedIn) SECTION_CHILD_ACCOUNT else SECTION_HOME
        showSection(restoredSection)
        handlePairingIntent(intent)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt(STATE_CURRENT_SECTION, currentSection)
        super.onSaveInstanceState(outState)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handlePairingIntent(intent)
    }

    override fun onResume() {
        super.onResume()
        populateFields()
        updateRoleUi()
        if (Prefs.isChildRole(this)) {
            IngestionClient.flushQueuedNotifications(this) { _, message ->
                runOnUiThread {
                    statusText.text = message
                    recentLogText.text = RecentNotificationLog.render(this)
                    childSetupStatusText.text = buildChildSetupStatus()
                    parentCaptureStatusText.text = buildParentCaptureStatus()
                }
            }
        }
    }

    private fun populateFields() {
        isPopulatingFields = true
        baseUrlInput.setText(Prefs.getBaseUrl(this))
        tokenInput.setText(Prefs.getDeviceToken(this))
        deviceNameInput.setText(Prefs.getDeviceName(this))
        parentIdentifierInput.setText(Prefs.getParentIdentifier(this))
        allowedPackagesInput.setText(Prefs.getAllowedPackages(this))
        blockedPackagesInput.setText(Prefs.getBlockedPackages(this))
        statusText.text = Prefs.getLastStatus(this)
        recentLogText.text = RecentNotificationLog.render(this)
        childSetupStatusText.text = buildChildSetupStatus()
        parentCaptureStatusText.text = buildParentCaptureStatus()
        darkModeSwitch.isChecked = Prefs.isDarkMode(this)
        languageSwitch.isChecked = Prefs.getLanguage(this) == "sw"
        inAppSoundsSwitch.isChecked = Prefs.inAppSoundsEnabled(this)
        isPopulatingFields = false
        updateSaveButtonVisibility()
    }

    private fun restoreChildSessionUi() {
        if (!childSignedIn) return
        val childUsername = Prefs.getChildUsername(this)
        val parentContact = Prefs.getChildParentContact(this)
        if (childUsername.isNotBlank()) {
            childUsernameInput.setText(childUsername)
            profileNameInput.setText(childUsername)
            childGreetingText.text = getString(R.string.child_greeting_live, childUsername)
        }
        if (parentContact.isNotBlank()) {
            childParentContactInput.setText(parentContact)
            profileContactInput.setText(parentContact)
        }
    }

    private fun updateRoleUi() {
        roleBadge.text = ""
        roleBadge.visibility = View.INVISIBLE
        roleSummaryText.text = getString(R.string.role_child_copy)
        captureRoleHint.text = getString(R.string.actions_section_copy)

        setRoleButtonState(parentRoleButton, false)
        setRoleButtonState(childRoleButton, true)

        parentChildDeviceNameInput.visibility = View.GONE
        createChildDeviceLinkButton.visibility = View.GONE
        copyPairingLinkButton.visibility = View.GONE
        sharePairingLinkButton.visibility = View.GONE
        openChildDevicesButton.visibility = View.GONE
        scanQrButton.visibility = View.VISIBLE
        updateMenuAccess()

        if (currentSection == SECTION_AUTH || currentSection == SECTION_REGISTER || currentSection == SECTION_PARENT_DASHBOARD) {
            currentSection = SECTION_HOME
        }
        syncDrawerState(currentSection)
        showSection(currentSection)
    }

    private fun isSignedIn(): Boolean = childSignedIn

    private fun updateMenuAccess() {
        val signedIn = isSignedIn()
        menuToggle.visibility = if (signedIn) View.VISIBLE else View.INVISIBLE
        menuToggle.isEnabled = signedIn
        drawerLayout.setDrawerLockMode(
            if (signedIn) DrawerLayout.LOCK_MODE_UNLOCKED else DrawerLayout.LOCK_MODE_LOCKED_CLOSED,
        )
        if (!signedIn) {
            drawerLayout.closeDrawer(GravityCompat.START)
        }

        val menuItems = listOf(
            menuHome,
            menuAuth,
            menuQr,
            menuSettings,
            menuCapture,
            menuFilters,
            menuStatus,
            menuLog,
            menuProfile,
            menuPassword,
            menuLogout,
        )
        menuItems.forEach { it.visibility = View.GONE }
        openParentDashboardButton.visibility = View.GONE
        openParentAlertsButton.visibility = View.GONE
        refreshParentAlertsButton.visibility = View.GONE
        reviewLatestSafeButton.visibility = View.GONE
        approveLogoutButton.visibility = View.GONE
        denyLogoutButton.visibility = View.GONE
        if (!signedIn) return

        menuHome.visibility = View.VISIBLE
        menuQr.visibility = View.VISIBLE
        menuSettings.visibility = View.VISIBLE
        menuCapture.visibility = View.VISIBLE
        menuFilters.visibility = View.VISIBLE
        menuProfile.visibility = View.VISIBLE
        menuPassword.visibility = View.VISIBLE
        menuLogout.visibility = View.VISIBLE
        menuStatus.visibility = View.VISIBLE
        menuLog.visibility = View.VISIBLE
    }

    private fun updateTopNavigation() {
        val onHomeLikeScreen = currentSection == SECTION_HOME || currentSection == SECTION_CHILD_ACCOUNT
        backButton.visibility = if (!onHomeLikeScreen) View.VISIBLE else View.GONE
        menuToggle.visibility = if (isSignedIn() && onHomeLikeScreen) View.VISIBLE else View.INVISIBLE
    }

    private fun navigateBack() {
        when {
            childSignedIn -> showSection(SECTION_CHILD_ACCOUNT)
            currentSection == SECTION_REGISTER || currentSection == SECTION_CHILD_AUTH -> showSection(SECTION_HOME)
            else -> showSection(SECTION_HOME)
        }
    }

    private fun signOut() {
        if (childSignedIn) {
            ParentApiClient.requestChildLogout(this) { _, message ->
                runOnUiThread {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                    childSetupStatusText.text = message
                }
            }
            return
        }
        showSection(SECTION_HOME)
    }

    private fun saveProfile() {
        val name = profileNameInput.text.toString().trim()
        val contact = profileContactInput.text.toString().trim()
        if (name.isBlank()) {
            Toast.makeText(this, R.string.profile_name_required, Toast.LENGTH_SHORT).show()
            return
        }
        ParentApiClient.updateProfile(this, name, contact) { ok, message ->
            runOnUiThread {
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                if (ok) {
                    if (childSignedIn) childGreetingText.text = getString(R.string.child_greeting_live, name)
                }
            }
        }
    }

    private fun sendPasswordVerificationCode() {
        val channel = if (profileContactInput.text.toString().contains("@")) "email" else "phone"
        ParentApiClient.sendPasswordVerification(this, channel) { ok, message ->
            runOnUiThread {
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                if (ok) passwordVerificationCodeInput.requestFocus()
            }
        }
    }

    private fun confirmPasswordVerificationCode() {
        val code = passwordVerificationCodeInput.text.toString().trim()
        if (code.isBlank()) {
            Toast.makeText(this, R.string.password_code_required, Toast.LENGTH_SHORT).show()
            return
        }
        ParentApiClient.confirmPasswordVerification(this, code) { ok, message ->
            runOnUiThread {
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                if (ok) {
                    passwordVerificationCodeInput.text?.clear()
                    currentPasswordInput.requestFocus()
                }
            }
        }
    }

    private fun changePassword() {
        val currentPassword = currentPasswordInput.text.toString()
        val newPassword = newPasswordInput.text.toString()
        val confirmPassword = confirmNewPasswordInput.text.toString()
        if (currentPassword.isBlank() || newPassword.isBlank() || confirmPassword.isBlank()) {
            Toast.makeText(this, R.string.password_fields_required, Toast.LENGTH_SHORT).show()
            return
        }
        if (newPassword != confirmPassword) {
            Toast.makeText(this, R.string.passwords_do_not_match, Toast.LENGTH_SHORT).show()
            return
        }
        ParentApiClient.changePassword(this, currentPassword, newPassword) { ok, message ->
            runOnUiThread {
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                if (ok) {
                    currentPasswordInput.text?.clear()
                    newPasswordInput.text?.clear()
                    confirmNewPasswordInput.text?.clear()
                    showSection(SECTION_SETTINGS)
                }
            }
        }
    }

    private fun setRoleButtonState(button: Button, active: Boolean) {
        button.alpha = if (active) 1f else 0.72f
        button.isAllCaps = false
    }

    private fun setDeviceRole(role: String, showHome: Boolean = true) {
        Prefs.setDeviceRole(this, role)
        Toast.makeText(this, R.string.role_saved, Toast.LENGTH_SHORT).show()
        updateRoleUi()
        if (showHome) showSection(SECTION_HOME)
    }

    private fun showSection(position: Int) {
        val resolvedPosition = when {
            position == SECTION_AUTH -> SECTION_CHILD_AUTH
            position == SECTION_REGISTER -> SECTION_HOME
            position == SECTION_PARENT_DASHBOARD -> SECTION_HOME
            position == SECTION_CHILD_ACCOUNT && !childSignedIn -> SECTION_HOME
            position == SECTION_PROFILE && !isSignedIn() -> SECTION_HOME
            position == SECTION_PASSWORD && !isSignedIn() -> SECTION_HOME
            position == SECTION_QR && childSignedIn -> SECTION_QR
            position == SECTION_QR && !childSignedIn -> SECTION_HOME
            (position == SECTION_CAPTURE || position == SECTION_FILTERS) && !childSignedIn -> SECTION_HOME
            (position == SECTION_STATUS || position == SECTION_LOGS || position == SECTION_SETTINGS) && !childSignedIn -> SECTION_HOME
            else -> position
        }
        currentSection = resolvedPosition

        roleSection.visibility = if (resolvedPosition == SECTION_HOME) View.VISIBLE else View.GONE
        parentHomeSection.visibility = View.GONE
        parentDashboardSection.visibility = View.GONE
        childHomeSection.visibility =
            if (resolvedPosition == SECTION_CHILD_ACCOUNT) View.VISIBLE else View.GONE
        registerFamilySection.visibility = View.GONE
        childLoginSection.visibility = if (resolvedPosition == SECTION_CHILD_AUTH) View.VISIBLE else View.GONE
        qrSection.visibility = if (resolvedPosition == SECTION_QR) View.VISIBLE else View.GONE
        settingsSection.visibility = if (resolvedPosition == SECTION_SETTINGS) View.VISIBLE else View.GONE
        actionsSection.visibility = if (resolvedPosition == SECTION_CAPTURE) View.VISIBLE else View.GONE
        filtersSection.visibility = if (resolvedPosition == SECTION_FILTERS) View.VISIBLE else View.GONE
        statusSection.visibility = if (resolvedPosition == SECTION_STATUS) View.VISIBLE else View.GONE
        logSection.visibility = if (resolvedPosition == SECTION_LOGS) View.VISIBLE else View.GONE
        profileSection.visibility = if (resolvedPosition == SECTION_PROFILE) View.VISIBLE else View.GONE
        passwordSection.visibility = if (resolvedPosition == SECTION_PASSWORD) View.VISIBLE else View.GONE
        if (resolvedPosition == SECTION_QR) renderLatestPairingQr()
        syncDrawerState(resolvedPosition)
        updateTopNavigation()
        drawerLayout.closeDrawer(GravityCompat.START)
    }

    private fun syncDrawerState(position: Int) {
        updateDrawerItem(menuHome, position == SECTION_HOME || position == SECTION_CHILD_ACCOUNT)
        updateDrawerItem(menuAuth, position == SECTION_CHILD_AUTH)
        updateDrawerItem(menuQr, position == SECTION_QR)
        updateDrawerItem(menuSettings, position == SECTION_SETTINGS)
        updateDrawerItem(menuCapture, position == SECTION_CAPTURE)
        updateDrawerItem(menuFilters, position == SECTION_FILTERS)
        updateDrawerItem(menuStatus, position == SECTION_STATUS)
        updateDrawerItem(menuLog, position == SECTION_LOGS)
        updateDrawerItem(menuProfile, position == SECTION_PROFILE)
        updateDrawerItem(menuPassword, position == SECTION_PASSWORD)
        updateDrawerItem(menuLogout, false)
    }

    private fun updateDrawerItem(view: TextView, active: Boolean) {
        if (active) {
            view.setBackgroundResource(R.drawable.bg_nav_active)
            view.setTextColor(ContextCompat.getColor(this, R.color.cyber_mzazi_seed))
        } else {
            view.background = null
            view.setTextColor(ContextCompat.getColor(this, android.R.color.white))
        }
    }

    private fun saveSettings() {
        Prefs.setDeviceToken(this, tokenInput.text.toString().trim())
        Prefs.setDeviceName(this, deviceNameInput.text.toString().trim())
        Prefs.setAllowedPackages(this, allowedPackagesInput.text.toString().trim())
        Prefs.setBlockedPackages(this, blockedPackagesInput.text.toString().trim())
        Toast.makeText(this, R.string.settings_saved, Toast.LENGTH_SHORT).show()
        populateFields()
    }

    private fun registerSettingsDirtyWatchers() {
        val watcher = object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                if (!isPopulatingFields) updateSaveButtonVisibility()
            }
            override fun afterTextChanged(s: Editable?) = Unit
        }
        listOf(
            tokenInput,
            deviceNameInput,
            allowedPackagesInput,
            blockedPackagesInput,
        ).forEach { it.addTextChangedListener(watcher) }
    }

    private fun updateSaveButtonVisibility() {
        saveButton.visibility = if (hasUnsavedSettings()) View.VISIBLE else View.GONE
    }

    private fun hasUnsavedSettings(): Boolean =
        tokenInput.text.toString().trim() != Prefs.getDeviceToken(this) ||
            deviceNameInput.text.toString().trim() != Prefs.getDeviceName(this) ||
            allowedPackagesInput.text.toString().trim() != Prefs.getAllowedPackages(this) ||
            blockedPackagesInput.text.toString().trim() != Prefs.getBlockedPackages(this)

    private fun buildParentCaptureStatus(): String {
        val notificationAccessEnabled = isNotificationListenerEnabled()
        return if (notificationAccessEnabled) {
            getString(R.string.parent_capture_status_enabled)
        } else {
            getString(R.string.parent_capture_status_disabled)
        }
    }
    private fun buildChildSetupStatus(): String {
        val tokenReady = Prefs.getDeviceToken(this).isNotBlank()
        val deviceNameReady = Prefs.getDeviceName(this).isNotBlank()
        val notificationAccessReady = isNotificationListenerEnabled()
        val allowedCount = FilterRules.normalizePackages(Prefs.getAllowedPackages(this)).size
        val blockedCount = FilterRules.normalizePackages(Prefs.getBlockedPackages(this)).size
        val queueCount = NotificationQueueStore.getQueue(this).size
        val deviceLabel = Prefs.getDeviceName(this).ifBlank { getString(R.string.this_phone) }
        val lines = listOf(
            if (tokenReady && deviceNameReady) {
                getString(R.string.child_status_device_connected, deviceLabel)
            } else {
                getString(R.string.child_status_pairing_needed)
            },
            if (notificationAccessReady) {
                getString(R.string.child_status_notifications_on)
            } else {
                getString(R.string.child_status_notifications_needed)
            },
            if (allowedCount > 0 || blockedCount > 0) {
                getString(R.string.child_status_filters_active, allowedCount, blockedCount)
            } else {
                getString(R.string.child_status_filters_default)
            },
            if (queueCount == 0) {
                getString(R.string.child_status_sync_clear)
            } else {
                getString(R.string.child_status_sync_waiting, queueCount)
            },
        )
        return lines.joinToString("\n")
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val enabledListeners = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
            ?: return false
        return enabledListeners.contains(packageName, ignoreCase = true)
    }

    private fun openWebPath(path: String) {
        val baseUrl = Prefs.getBaseUrl(this).trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            Toast.makeText(this, R.string.base_url_required, Toast.LENGTH_SHORT).show()
            return
        }
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("$baseUrl$path")))
    }

    private fun signInParent() {
        Toast.makeText(this, R.string.child_only_app_notice, Toast.LENGTH_SHORT).show()
        showSection(SECTION_CHILD_AUTH)
    }

    private fun registerFamilyAccount() {
        val familyName = registerFamilyNameInput.text.toString().trim()
        val parentName = registerParentNameInput.text.toString().trim()
        val parentContact = registerParentContactInput.text.toString().trim()
        val parentPassword = registerParentPasswordInput.text.toString()
        val childName = registerChildNameInput.text.toString().trim()
        val childUsername = registerChildUsernameInput.text.toString().trim()
        val childPassword = registerChildPasswordInput.text.toString()
        if (
            familyName.isBlank() ||
            parentName.isBlank() ||
            parentContact.isBlank() ||
            parentPassword.isBlank() ||
            childName.isBlank() ||
            childUsername.isBlank() ||
            childPassword.isBlank()
        ) {
            Toast.makeText(this, R.string.register_fields_required, Toast.LENGTH_SHORT).show()
            return
        }
        registerFamilyStatusText.text = getString(R.string.registering_family)
        registerFamilyButton.isEnabled = false
        ParentApiClient.registerFamily(
            context = this,
            familyName = familyName,
            parentName = parentName,
            parentContact = parentContact,
            parentPassword = parentPassword,
            childName = childName,
            childUsername = childUsername,
            childPassword = childPassword,
        ) { ok, message ->
            runOnUiThread {
                registerFamilyButton.isEnabled = true
                registerParentPasswordInput.text?.clear()
                registerChildPasswordInput.text?.clear()
                registerFamilyStatusText.text = message
                Toast.makeText(this, message.lines().firstOrNull().orEmpty(), Toast.LENGTH_SHORT).show()
                if (ok) {
                    childSignedIn = false
                    setDeviceRole(Prefs.ROLE_CHILD, showHome = false)
                    showSection(SECTION_CHILD_AUTH)
                }
            }
        }
    }

    private fun signInChild() {
        val parentContact = childParentContactInput.text.toString().trim()
        val childUsername = childUsernameInput.text.toString().trim()
        val password = childPasswordInput.text.toString()
        if (parentContact.isBlank() || childUsername.isBlank() || password.isBlank()) {
            Toast.makeText(this, R.string.child_login_required, Toast.LENGTH_SHORT).show()
            return
        }
        childLoginStatusText.text = getString(R.string.child_signing_in)
        childLoginButton.isEnabled = false
        ParentApiClient.childLogin(this, parentContact, childUsername, password) { ok, message ->
            runOnUiThread {
                childLoginButton.isEnabled = true
                childPasswordInput.text?.clear()
                childLoginStatusText.text = message
                Toast.makeText(
                    this,
                    if (ok) R.string.child_sign_in_ok else R.string.child_sign_in_failed,
                    Toast.LENGTH_SHORT,
                ).show()
                if (ok) {
                    childSignedIn = true
                    Prefs.setChildSession(this, parentContact, childUsername)
                    profileNameInput.setText(childUsername)
                    profileContactInput.setText(parentContact)
                    childGreetingText.text = getString(R.string.child_greeting_live, childUsername)
                    setDeviceRole(Prefs.ROLE_CHILD, showHome = false)
                    updateMenuAccess()
                    showSection(SECTION_CHILD_ACCOUNT)
                }
            }
        }
    }

    private fun verifyParentPhone() {
        val identifier = parentIdentifierInput.text.toString().trim()
        val code = parentPhoneCodeInput.text.toString().trim()
        if (identifier.isBlank() || code.isBlank()) {
            Toast.makeText(this, R.string.phone_verification_required, Toast.LENGTH_SHORT).show()
            return
        }
        parentAlertSummaryText.text = getString(R.string.phone_verification_running)
        parentVerifyPhoneButton.isEnabled = false
        ParentApiClient.verifyPhone(this, identifier, code) { ok, message ->
            runOnUiThread {
                parentVerifyPhoneButton.isEnabled = true
                if (ok) parentPhoneCodeInput.text?.clear()
                parentAlertSummaryText.text = message
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun resendParentPhoneCode() {
        val identifier = parentIdentifierInput.text.toString().trim()
        if (identifier.isBlank()) {
            Toast.makeText(this, R.string.parent_phone_required, Toast.LENGTH_SHORT).show()
            return
        }
        parentAlertSummaryText.text = getString(R.string.phone_verification_sending)
        parentResendPhoneCodeButton.isEnabled = false
        ParentApiClient.resendPhoneVerification(this, identifier) { _, message ->
            runOnUiThread {
                parentResendPhoneCodeButton.isEnabled = true
                parentAlertSummaryText.text = message
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun refreshParentAlerts() {
        parentAlertSummaryText.text = getString(R.string.parent_alerts_loading)
        ParentApiClient.fetchDashboard(this) { ok, dashboard, message ->
            runOnUiThread {
                parentAlertSummaryText.text = message
                if (ok && dashboard != null) {
                    parentFamilyNameText.text = dashboard.familyName
                    parentChildStatusText.text = "${dashboard.childName} - Online"
                    parentAlertsWeekText.text = getString(R.string.alert_count_format, dashboard.alertCount)
                    parentRecentMessagesText.text = dashboard.recentMessages
                    parentDeviceStatusText.text = dashboard.deviceStatus
                }
                if (!ok) {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun runParentAction(action: ((Boolean, String) -> Unit) -> Unit) {
        parentAlertSummaryText.text = getString(R.string.parent_action_running)
        action { ok, message ->
            runOnUiThread {
                parentAlertSummaryText.text = message
                Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                if (ok) refreshParentAlerts()
            }
        }
    }

    private fun createChildDeviceLink() {
        val deviceName = parentChildDeviceNameInput.text.toString().trim()
        parentAlertSummaryText.text = getString(R.string.creating_child_device_link)
        createChildDeviceLinkButton.isEnabled = false
        ParentApiClient.createChildDeviceLink(this, deviceName) { _, message ->
            runOnUiThread {
                createChildDeviceLinkButton.isEnabled = true
                parentAlertSummaryText.text = message
                renderLatestPairingQr()
                Toast.makeText(this, message.lines().firstOrNull().orEmpty(), Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun copyLatestPairingLink() {
        val pairingUri = ParentApiClient.getLatestPairingUri()
        if (pairingUri.isBlank()) {
            Toast.makeText(this, R.string.no_pairing_link_ready, Toast.LENGTH_SHORT).show()
            return
        }
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(getString(R.string.pairing_link_label), pairingUri))
        Toast.makeText(this, R.string.pairing_link_copied, Toast.LENGTH_SHORT).show()
    }

    private fun shareLatestPairingLink() {
        val pairingUri = ParentApiClient.getLatestPairingUri()
        if (pairingUri.isBlank()) {
            Toast.makeText(this, R.string.no_pairing_link_ready, Toast.LENGTH_SHORT).show()
            return
        }
        val sendIntent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, pairingUri)
        }
        startActivity(Intent.createChooser(sendIntent, getString(R.string.share_pairing_link)))
    }

    private fun sendTestPayload() {
        if (hasUnsavedSettings()) {
            saveSettings()
        }
        val payload = NotificationPayload(
            appName = "Cyber Mzazi Test",
            appPackage = packageName,
            senderHandle = "Test Sender",
            notificationTitle = "Manual test",
            notificationText = "Do not tell your parents. Keep this secret.",
            deepLink = null,
        )
        IngestionClient.sendNotification(this, payload) { ok, message ->
            runOnUiThread {
                statusText.text = message
                recentLogText.text = RecentNotificationLog.render(this)
                childSetupStatusText.text = buildChildSetupStatus()
                parentCaptureStatusText.text = buildParentCaptureStatus()
                Toast.makeText(
                    this,
                    if (ok) R.string.test_sent_ok else R.string.test_sent_failed,
                    Toast.LENGTH_SHORT,
                ).show()
            }
        }
    }

    private fun retryQueue() {
        IngestionClient.flushQueuedNotifications(this) { ok, message ->
            runOnUiThread {
                statusText.text = message
                recentLogText.text = RecentNotificationLog.render(this)
                childSetupStatusText.text = buildChildSetupStatus()
                parentCaptureStatusText.text = buildParentCaptureStatus()
                Toast.makeText(
                    this,
                    if (ok) R.string.retry_queue_ok else R.string.retry_queue_partial,
                    Toast.LENGTH_SHORT,
                ).show()
            }
        }
    }

    private fun startQrPairing() {
        when {
            ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED ->
                launchQrScanner()
            else -> cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun launchQrScanner() {
        val options = ScanOptions().apply {
            setDesiredBarcodeFormats(ScanOptions.QR_CODE)
            setPrompt(getString(R.string.scan_qr_prompt))
            setBeepEnabled(false)
            setOrientationLocked(false)
        }
        scanLauncher.launch(options)
    }

    private fun applyPairingPayload(contents: String) {
        val uri = Uri.parse(contents)
        if (uri.scheme != "cybermzazi") {
            Toast.makeText(this, R.string.invalid_pairing_qr, Toast.LENGTH_SHORT).show()
            return
        }
        baseUrlInput.setText(Prefs.getBaseUrl(this))
        tokenInput.setText(uri.getQueryParameter("token").orEmpty())
        val qrDeviceName = uri.getQueryParameter("device_name").orEmpty()
        if (deviceNameInput.text.isNullOrBlank()) {
            deviceNameInput.setText(qrDeviceName)
        }
        when (uri.getQueryParameter("role").orEmpty().trim().lowercase()) {
            Prefs.ROLE_PARENT -> Prefs.setDeviceRole(this, Prefs.ROLE_PARENT)
            Prefs.ROLE_CHILD -> Prefs.setDeviceRole(this, Prefs.ROLE_CHILD)
        }
        saveSettings()
        updateRoleUi()
        Toast.makeText(this, R.string.qr_pairing_applied, Toast.LENGTH_SHORT).show()
    }

    private fun renderLatestPairingQr() {
        val pairingUri = ParentApiClient.getLatestPairingUri()
        if (pairingUri.isBlank()) {
            pairingQrImage.setImageResource(R.drawable.cyber_mzazi_logo)
            pairingLinkText.visibility = View.GONE
            return
        }
        val bitmap = BarcodeEncoder().encodeBitmap(pairingUri, BarcodeFormat.QR_CODE, 720, 720)
        pairingQrImage.setImageBitmap(bitmap)
        pairingLinkText.text = pairingUri
        pairingLinkText.visibility = View.VISIBLE
    }

    private fun handlePairingIntent(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme == "cybermzazi" && uri.host == "pair") {
            applyPairingPayload(uri.toString())
            intent.data = null
        }
    }

    companion object {
        private const val SECTION_HOME = 0
        private const val SECTION_AUTH = 1
        private const val SECTION_QR = 2
        private const val SECTION_SETTINGS = 3
        private const val SECTION_CAPTURE = 4
        private const val SECTION_FILTERS = 5
        private const val SECTION_STATUS = 6
        private const val SECTION_LOGS = 7
        private const val SECTION_REGISTER = 8
        private const val SECTION_CHILD_AUTH = 9
        private const val SECTION_CHILD_ACCOUNT = 10
        private const val SECTION_PARENT_DASHBOARD = 11
        private const val SECTION_PROFILE = 12
        private const val SECTION_PASSWORD = 13
        private const val STATE_CURRENT_SECTION = "current_section"
    }
}
