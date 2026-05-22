package com.cybermzazi.companion

import android.Manifest
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
import android.widget.ProgressBar
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
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

class MainActivity : AppCompatActivity() {

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var backButton: TextView
    private lateinit var menuToggle: TextView
    private lateinit var roleBadge: TextView
    private lateinit var roleSummaryText: TextView
    private lateinit var captureRoleHint: TextView
    private lateinit var tokenInput: EditText
    private lateinit var deviceNameInput: EditText
    private lateinit var childStatusOverviewText: TextView
    private lateinit var childStatusDeviceText: TextView
    private lateinit var childStatusNotificationsText: TextView
    private lateinit var childStatusLogoutText: TextView
    private lateinit var childStatusFiltersText: TextView
    private lateinit var childStatusSyncText: TextView
    private lateinit var childSetupStatusText: TextView
    private lateinit var childGreetingText: TextView
    private lateinit var childTopStatusBadgeText: TextView
    private lateinit var childSetupProgressText: TextView
    private lateinit var childSetupProgressBar: ProgressBar
    private lateinit var childPairingChecklistText: TextView
    private lateinit var childNotificationChecklistText: TextView
    private lateinit var childFiltersChecklistText: TextView
    private lateinit var childAccountChecklistText: TextView
    private lateinit var childConnectionCardText: TextView
    private lateinit var childNotificationCardText: TextView
    private lateinit var childSyncCardText: TextView
    private lateinit var childFiltersCardText: TextView
    private lateinit var childParentContactInput: EditText
    private lateinit var childUsernameInput: EditText
    private lateinit var childPasswordInput: EditText
    private lateinit var childLoginStatusText: TextView
    private lateinit var allowedPackagesInput: EditText
    private lateinit var blockedPackagesInput: EditText
    private lateinit var statusText: TextView
    private lateinit var recentLogText: TextView
    private lateinit var pairingQrImage: ImageView
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
    private lateinit var childHomeSection: View
    private lateinit var childLoginSection: View
    private lateinit var profileSection: View
    private lateinit var passwordSection: View

    private lateinit var openChildLoginButton: Button
    private lateinit var childLoginButton: Button
    private lateinit var openNotificationSettingsButton: Button
    private lateinit var statusPairDeviceButton: Button
    private lateinit var goPairChildButton: Button
    private lateinit var goCaptureChildButton: Button
    private lateinit var goFiltersChildButton: Button
    private lateinit var saveButton: Button
    private lateinit var scanQrButton: Button
    private lateinit var passwordConfirmCodeButton: Button

    private var currentSection = 0
    private var isPopulatingFields = false
    private var childSignedIn = false
    private var latestChildLogoutStatus: String? = null

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
        tokenInput = findViewById(R.id.tokenInput)
        deviceNameInput = findViewById(R.id.deviceNameInput)
        childStatusOverviewText = findViewById(R.id.childStatusOverviewText)
        childStatusDeviceText = findViewById(R.id.childStatusDeviceText)
        childStatusNotificationsText = findViewById(R.id.childStatusNotificationsText)
        childStatusLogoutText = findViewById(R.id.childStatusLogoutText)
        childStatusFiltersText = findViewById(R.id.childStatusFiltersText)
        childStatusSyncText = findViewById(R.id.childStatusSyncText)
        childSetupStatusText = findViewById(R.id.childSetupStatusText)
        childGreetingText = findViewById(R.id.childGreetingText)
        childTopStatusBadgeText = findViewById(R.id.childTopStatusBadgeText)
        childSetupProgressText = findViewById(R.id.childSetupProgressText)
        childSetupProgressBar = findViewById(R.id.childSetupProgressBar)
        childPairingChecklistText = findViewById(R.id.childPairingChecklistText)
        childNotificationChecklistText = findViewById(R.id.childNotificationChecklistText)
        childFiltersChecklistText = findViewById(R.id.childFiltersChecklistText)
        childAccountChecklistText = findViewById(R.id.childAccountChecklistText)
        childConnectionCardText = findViewById(R.id.childConnectionCardText)
        childNotificationCardText = findViewById(R.id.childNotificationCardText)
        childSyncCardText = findViewById(R.id.childSyncCardText)
        childFiltersCardText = findViewById(R.id.childFiltersCardText)
        childParentContactInput = findViewById(R.id.childParentContactInput)
        childUsernameInput = findViewById(R.id.childUsernameInput)
        childPasswordInput = findViewById(R.id.childPasswordInput)
        childLoginStatusText = findViewById(R.id.childLoginStatusText)
        allowedPackagesInput = findViewById(R.id.allowedPackagesInput)
        blockedPackagesInput = findViewById(R.id.blockedPackagesInput)
        statusText = findViewById(R.id.statusText)
        recentLogText = findViewById(R.id.recentLogText)
        pairingQrImage = findViewById(R.id.pairingQrImage)
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
        childHomeSection = findViewById(R.id.childHomeSection)
        childLoginSection = findViewById(R.id.childLoginSection)
        profileSection = findViewById(R.id.profileSection)
        passwordSection = findViewById(R.id.passwordSection)
        openChildLoginButton = findViewById(R.id.openChildLoginButton)
        childLoginButton = findViewById(R.id.childLoginButton)
        openNotificationSettingsButton = findViewById(R.id.openNotificationSettingsButton)
        statusPairDeviceButton = findViewById(R.id.statusPairDeviceButton)
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
        childLoginButton.setOnClickListener { signInChild() }
        openNotificationSettingsButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        statusPairDeviceButton.setOnClickListener { showSection(SECTION_QR) }
        goPairChildButton.setOnClickListener { signOut() }
        goCaptureChildButton.setOnClickListener { showSection(SECTION_CAPTURE) }
        goFiltersChildButton.setOnClickListener { showSection(SECTION_SETTINGS) }

        saveButton.setOnClickListener { saveSettings() }
        scanQrButton.setOnClickListener { startQrPairing() }
        findViewById<Button>(R.id.notificationAccessButton).setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        findViewById<Button>(R.id.sendTestButton).setOnClickListener {
            sendTestPayload()
        }
        findViewById<Button>(R.id.retryQueueButton).setOnClickListener {
            retryQueue()
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
        Prefs.setDeviceRole(this)
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
        IngestionClient.flushQueuedNotifications(this) { _, message ->
            runOnUiThread {
                statusText.text = message
                recentLogText.text = RecentNotificationLog.render(this)
                childSetupStatusText.text = buildChildSetupStatus()
                updateChildDashboardCards()
            }
        }
        checkChildLogoutDecision()
    }

    private fun populateFields() {
        isPopulatingFields = true
        tokenInput.setText(Prefs.getDeviceToken(this))
        deviceNameInput.setText(Prefs.getDeviceName(this))
        allowedPackagesInput.setText(Prefs.getAllowedPackages(this))
        blockedPackagesInput.setText(Prefs.getBlockedPackages(this))
        statusText.text = Prefs.getLastStatus(this)
        recentLogText.text = RecentNotificationLog.render(this)
        childSetupStatusText.text = buildChildSetupStatus()
        updateChildDashboardCards()
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

        scanQrButton.visibility = View.VISIBLE
        updateMenuAccess()

        if (currentSection == SECTION_AUTH) {
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
            currentSection == SECTION_CHILD_AUTH -> showSection(SECTION_HOME)
            else -> showSection(SECTION_HOME)
        }
    }

    private fun signOut() {
        if (childSignedIn) {
            ParentApiClient.requestChildLogout(this) { ok, message ->
                runOnUiThread {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                    if (ok) latestChildLogoutStatus = "pending"
                    updateChildDashboardCards()
                }
            }
            return
        }
        showSection(SECTION_HOME)
    }

    private fun checkChildLogoutDecision() {
        if (!childSignedIn) return
        ParentApiClient.fetchChildLogoutStatus(this) { ok, status, _ ->
            if (!ok) return@fetchChildLogoutStatus
            runOnUiThread {
                when (status) {
                    "approved" -> completeApprovedChildLogout()
                    "denied" -> {
                        latestChildLogoutStatus = "denied"
                        updateChildDashboardCards()
                        childSetupStatusText.text = getString(R.string.child_logout_denied_status)
                    }
                    "pending" -> {
                        latestChildLogoutStatus = "pending"
                        updateChildDashboardCards()
                    }
                    else -> {
                        latestChildLogoutStatus = null
                        updateChildDashboardCards()
                    }
                }
            }
        }
    }

    private fun completeApprovedChildLogout() {
        ParentApiClient.logout(this) { ok, message ->
            runOnUiThread {
                if (ok) {
                    childSignedIn = false
                    Prefs.clearChildSession(this)
                    Prefs.clearParentSession(this)
                    latestChildLogoutStatus = null
                    updateMenuAccess()
                    showSection(SECTION_HOME)
                    Toast.makeText(this, R.string.child_logout_approved_signed_out, Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
                }
            }
        }
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

    private fun refreshChildRole(showHome: Boolean = true) {
        Prefs.setDeviceRole(this)
        updateRoleUi()
        if (showHome) showSection(SECTION_HOME)
    }

    private fun showSection(position: Int) {
        val resolvedPosition = when {
            position == SECTION_AUTH -> SECTION_CHILD_AUTH
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
        childHomeSection.visibility =
            if (resolvedPosition == SECTION_CHILD_ACCOUNT) View.VISIBLE else View.GONE
        childLoginSection.visibility = if (resolvedPosition == SECTION_CHILD_AUTH) View.VISIBLE else View.GONE
        qrSection.visibility = if (resolvedPosition == SECTION_QR) View.VISIBLE else View.GONE
        settingsSection.visibility = if (resolvedPosition == SECTION_SETTINGS) View.VISIBLE else View.GONE
        actionsSection.visibility = if (resolvedPosition == SECTION_CAPTURE) View.VISIBLE else View.GONE
        filtersSection.visibility = if (resolvedPosition == SECTION_FILTERS) View.VISIBLE else View.GONE
        statusSection.visibility = if (resolvedPosition == SECTION_STATUS) View.VISIBLE else View.GONE
        logSection.visibility = if (resolvedPosition == SECTION_LOGS) View.VISIBLE else View.GONE
        profileSection.visibility = if (resolvedPosition == SECTION_PROFILE) View.VISIBLE else View.GONE
        passwordSection.visibility = if (resolvedPosition == SECTION_PASSWORD) View.VISIBLE else View.GONE
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

    private fun updateChildDashboardCards() {
        val tokenReady = Prefs.getDeviceToken(this).isNotBlank()
        val deviceName = Prefs.getDeviceName(this).ifBlank { getString(R.string.this_phone) }
        val paired = tokenReady && Prefs.getDeviceName(this).isNotBlank()
        val notificationAccessReady = isNotificationListenerEnabled()
        val allowedCount = FilterRules.normalizePackages(Prefs.getAllowedPackages(this)).size
        val blockedCount = FilterRules.normalizePackages(Prefs.getBlockedPackages(this)).size
        val queueCount = NotificationQueueStore.getQueue(this).size
        val accountLinked = childSignedIn
        val filtersReady = true
        val doneCount = listOf(paired, notificationAccessReady, filtersReady, accountLinked).count { it }
        val syncText = if (queueCount == 0) {
            getString(R.string.child_sync_card_clear)
        } else {
            getString(R.string.child_sync_card_waiting, queueCount)
        }
        val logoutText = when (latestChildLogoutStatus) {
            "pending" -> getString(R.string.child_logout_pending_card_rich)
            "denied" -> getString(R.string.child_logout_denied_card_rich)
            else -> getString(R.string.child_logout_no_request_card_rich)
        }

        childTopStatusBadgeText.text = when {
            !childSignedIn -> getString(R.string.child_badge_offline)
            queueCount == 0 -> getString(R.string.child_badge_online_synced)
            else -> getString(R.string.child_badge_online_sync_pending)
        }
        childSetupProgressText.text = getString(R.string.child_setup_done_count, doneCount, 4)
        childSetupProgressBar.progress = doneCount
        childPairingChecklistText.text = setupLine(
            paired,
            getString(R.string.child_setup_finish_pairing),
            getString(R.string.child_setup_device_paired),
        )
        childNotificationChecklistText.text = setupLine(
            notificationAccessReady,
            getString(R.string.child_setup_turn_on_notifications),
            getString(R.string.child_setup_notifications_enabled),
        )
        childFiltersChecklistText.text = setupLine(true, getString(R.string.child_setup_filters_synced))
        childAccountChecklistText.text = setupLine(accountLinked, getString(R.string.child_setup_account_linked))

        childConnectionCardText.text = if (paired) {
            getString(R.string.child_connection_card_paired_rich, deviceName)
        } else {
            getString(R.string.child_connection_card_not_paired_rich)
        }
        childNotificationCardText.text = if (notificationAccessReady) {
            getString(R.string.child_notification_card_on_rich)
        } else {
            getString(R.string.child_notification_card_needed_rich)
        }
        childSyncCardText.text = logoutText
        childFiltersCardText.text = if (allowedCount > 0 || blockedCount > 0) {
            getString(R.string.child_filters_card_custom, allowedCount, blockedCount)
        } else {
            getString(R.string.child_filters_card_default)
        }
        childStatusOverviewText.text = getString(
            R.string.child_status_overview,
            doneCount,
            4,
            childTopStatusBadgeText.text,
        )
        childStatusDeviceText.text = childConnectionCardText.text
        childStatusNotificationsText.text = childNotificationCardText.text
        childStatusLogoutText.text = logoutText
        childStatusFiltersText.text = childFiltersCardText.text
        childStatusSyncText.text = syncText
    }

    private fun setupLine(done: Boolean, label: String, doneLabel: String = label): String {
        val marker = if (done) "[OK]" else "[!]"
        return "$marker ${if (done) doneLabel else label}"
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val enabledListeners = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
            ?: return false
        return enabledListeners.contains(packageName, ignoreCase = true)
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
                    refreshChildRole(showHome = false)
                    updateMenuAccess()
                    showSection(SECTION_CHILD_ACCOUNT)
                }
            }
        }
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
                updateChildDashboardCards()
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
                updateChildDashboardCards()
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
        tokenInput.setText(uri.getQueryParameter("token").orEmpty())
        val qrDeviceName = uri.getQueryParameter("device_name").orEmpty()
        if (deviceNameInput.text.isNullOrBlank()) {
            deviceNameInput.setText(qrDeviceName)
        }
        Prefs.setDeviceRole(this)
        saveSettings()
        updateRoleUi()
        Toast.makeText(this, R.string.qr_pairing_applied, Toast.LENGTH_SHORT).show()
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
        private const val SECTION_CHILD_AUTH = 9
        private const val SECTION_CHILD_ACCOUNT = 10
        private const val SECTION_PROFILE = 12
        private const val SECTION_PASSWORD = 13
        private const val STATE_CURRENT_SECTION = "current_section"
    }
}
