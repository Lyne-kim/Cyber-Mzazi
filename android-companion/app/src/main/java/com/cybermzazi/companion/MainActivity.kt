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
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

class MainActivity : AppCompatActivity() {

    private lateinit var drawerLayout: DrawerLayout
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
    private lateinit var parentChildDeviceNameInput: EditText
    private lateinit var parentAlertSummaryText: TextView
    private lateinit var parentCaptureStatusText: TextView
    private lateinit var childSetupStatusText: TextView
    private lateinit var allowedPackagesInput: EditText
    private lateinit var blockedPackagesInput: EditText
    private lateinit var statusText: TextView
    private lateinit var recentLogText: TextView

    private lateinit var menuHome: TextView
    private lateinit var menuAuth: TextView
    private lateinit var menuQr: TextView
    private lateinit var menuSettings: TextView
    private lateinit var menuCapture: TextView
    private lateinit var menuFilters: TextView
    private lateinit var menuStatus: TextView
    private lateinit var menuLog: TextView

    private lateinit var roleSection: View
    private lateinit var qrSection: View
    private lateinit var settingsSection: View
    private lateinit var actionsSection: View
    private lateinit var filtersSection: View
    private lateinit var statusSection: View
    private lateinit var logSection: View
    private lateinit var parentHomeSection: View
    private lateinit var childHomeSection: View

    private lateinit var openParentDashboardButton: Button
    private lateinit var openParentAlertsButton: Button
    private lateinit var openChildDevicesButton: Button
    private lateinit var parentLoginButton: Button
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

    private var currentSection = 0
    private var isPopulatingFields = false

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
        setContentView(R.layout.activity_main)

        drawerLayout = findViewById(R.id.drawerLayout)
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
        parentChildDeviceNameInput = findViewById(R.id.parentChildDeviceNameInput)
        parentAlertSummaryText = findViewById(R.id.parentAlertSummaryText)
        parentCaptureStatusText = findViewById(R.id.parentCaptureStatusText)
        childSetupStatusText = findViewById(R.id.childSetupStatusText)
        allowedPackagesInput = findViewById(R.id.allowedPackagesInput)
        blockedPackagesInput = findViewById(R.id.blockedPackagesInput)
        statusText = findViewById(R.id.statusText)
        recentLogText = findViewById(R.id.recentLogText)

        menuHome = findViewById(R.id.menuHome)
        menuAuth = findViewById(R.id.menuAuth)
        menuQr = findViewById(R.id.menuQr)
        menuSettings = findViewById(R.id.menuSettings)
        menuCapture = findViewById(R.id.menuCapture)
        menuFilters = findViewById(R.id.menuFilters)
        menuStatus = findViewById(R.id.menuStatus)
        menuLog = findViewById(R.id.menuLog)

        roleSection = findViewById(R.id.roleSection)
        qrSection = findViewById(R.id.qrSection)
        settingsSection = findViewById(R.id.settingsSection)
        actionsSection = findViewById(R.id.actionsSection)
        filtersSection = findViewById(R.id.filtersSection)
        statusSection = findViewById(R.id.statusSection)
        logSection = findViewById(R.id.logSection)
        parentHomeSection = findViewById(R.id.parentHomeSection)
        childHomeSection = findViewById(R.id.childHomeSection)

        openParentDashboardButton = findViewById(R.id.openParentDashboardButton)
        openParentAlertsButton = findViewById(R.id.openParentAlertsButton)
        openChildDevicesButton = findViewById(R.id.openChildDevicesButton)
        parentLoginButton = findViewById(R.id.parentLoginButton)
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

        menuToggle.setOnClickListener {
            if (drawerLayout.isDrawerOpen(GravityCompat.START)) {
                drawerLayout.closeDrawer(GravityCompat.START)
            } else {
                drawerLayout.openDrawer(GravityCompat.START)
            }
        }

        menuHome.setOnClickListener { showSection(SECTION_HOME) }
        menuAuth.setOnClickListener { showSection(SECTION_AUTH) }
        menuQr.setOnClickListener { showSection(SECTION_QR) }
        menuSettings.setOnClickListener { showSection(SECTION_SETTINGS) }
        menuCapture.setOnClickListener { showSection(SECTION_CAPTURE) }
        menuFilters.setOnClickListener { showSection(SECTION_FILTERS) }
        menuStatus.setOnClickListener { showSection(SECTION_STATUS) }
        menuLog.setOnClickListener { showSection(SECTION_LOGS) }

        parentRoleButton.setOnClickListener { setDeviceRole(Prefs.ROLE_PARENT) }
        childRoleButton.setOnClickListener { setDeviceRole(Prefs.ROLE_CHILD) }

        openParentDashboardButton.setOnClickListener { openWebPath("/parent/dashboard") }
        openParentAlertsButton.setOnClickListener { openWebPath("/parent/alerts") }
        openChildDevicesButton.setOnClickListener { openWebPath("/parent/child-profile") }
        parentLoginButton.setOnClickListener { signInParent() }
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
        goPairChildButton.setOnClickListener { showSection(SECTION_QR) }
        goCaptureChildButton.setOnClickListener { showSection(SECTION_CAPTURE) }
        goFiltersChildButton.setOnClickListener { showSection(SECTION_FILTERS) }

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

        registerSettingsDirtyWatchers()
        populateFields()
        updateRoleUi()
        showSection(SECTION_HOME)
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
        isPopulatingFields = false
        updateSaveButtonVisibility()
    }

    private fun updateRoleUi() {
        val isChildRole = Prefs.isChildRole(this)
        roleBadge.text = getString(if (isChildRole) R.string.role_child else R.string.role_parent)
        roleSummaryText.text = getString(if (isChildRole) R.string.role_child_copy else R.string.role_parent_copy)
        captureRoleHint.text = getString(if (isChildRole) R.string.actions_section_copy else R.string.parent_mode_capture_disabled)

        setRoleButtonState(parentRoleButton, !isChildRole)
        setRoleButtonState(childRoleButton, isChildRole)

        menuAuth.visibility = if (isChildRole) View.GONE else View.VISIBLE
        menuCapture.visibility = if (isChildRole) View.VISIBLE else View.GONE
        menuFilters.visibility = if (isChildRole) View.VISIBLE else View.GONE
        parentChildDeviceNameInput.visibility = if (isChildRole) View.GONE else View.VISIBLE
        createChildDeviceLinkButton.visibility = if (isChildRole) View.GONE else View.VISIBLE
        copyPairingLinkButton.visibility = if (isChildRole) View.GONE else View.VISIBLE
        sharePairingLinkButton.visibility = if (isChildRole) View.GONE else View.VISIBLE
        openChildDevicesButton.visibility = if (isChildRole) View.GONE else View.VISIBLE
        scanQrButton.visibility = if (isChildRole) View.VISIBLE else View.GONE

        if (!isChildRole && (currentSection == SECTION_CAPTURE || currentSection == SECTION_FILTERS)) {
            currentSection = SECTION_HOME
        }
        if (isChildRole && currentSection == SECTION_AUTH) {
            currentSection = SECTION_HOME
        }
        syncDrawerState(currentSection)
        showSection(currentSection)
    }

    private fun setRoleButtonState(button: Button, active: Boolean) {
        button.alpha = if (active) 1f else 0.72f
        button.isAllCaps = false
    }

    private fun setDeviceRole(role: String) {
        Prefs.setDeviceRole(this, role)
        Toast.makeText(this, R.string.role_saved, Toast.LENGTH_SHORT).show()
        updateRoleUi()
    }

    private fun showSection(position: Int) {
        val isChildRole = Prefs.isChildRole(this)
        val resolvedPosition = when {
            !isChildRole && (position == SECTION_CAPTURE || position == SECTION_FILTERS) -> SECTION_HOME
            isChildRole && position == SECTION_AUTH -> SECTION_HOME
            else -> position
        }
        currentSection = resolvedPosition

        roleSection.visibility = if (resolvedPosition == SECTION_HOME) View.VISIBLE else View.GONE
        parentHomeSection.visibility =
            if (resolvedPosition == SECTION_AUTH && Prefs.isParentRole(this)) View.VISIBLE else View.GONE
        childHomeSection.visibility =
            if (resolvedPosition == SECTION_HOME && Prefs.isChildRole(this)) View.VISIBLE else View.GONE
        qrSection.visibility = if (resolvedPosition == SECTION_QR) View.VISIBLE else View.GONE
        settingsSection.visibility = if (resolvedPosition == SECTION_SETTINGS) View.VISIBLE else View.GONE
        actionsSection.visibility = if (resolvedPosition == SECTION_CAPTURE && Prefs.isChildRole(this)) View.VISIBLE else View.GONE
        filtersSection.visibility = if (resolvedPosition == SECTION_FILTERS && Prefs.isChildRole(this)) View.VISIBLE else View.GONE
        statusSection.visibility = if (resolvedPosition == SECTION_STATUS) View.VISIBLE else View.GONE
        logSection.visibility = if (resolvedPosition == SECTION_LOGS) View.VISIBLE else View.GONE
        syncDrawerState(resolvedPosition)
        drawerLayout.closeDrawer(GravityCompat.START)
    }

    private fun syncDrawerState(position: Int) {
        updateDrawerItem(menuHome, position == SECTION_HOME)
        updateDrawerItem(menuAuth, position == SECTION_AUTH)
        updateDrawerItem(menuQr, position == SECTION_QR)
        updateDrawerItem(menuSettings, position == SECTION_SETTINGS)
        updateDrawerItem(menuCapture, position == SECTION_CAPTURE)
        updateDrawerItem(menuFilters, position == SECTION_FILTERS)
        updateDrawerItem(menuStatus, position == SECTION_STATUS)
        updateDrawerItem(menuLog, position == SECTION_LOGS)
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
        Prefs.setBaseUrl(this, baseUrlInput.text.toString().trim())
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
            baseUrlInput,
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
        baseUrlInput.text.toString().trim() != Prefs.getBaseUrl(this) ||
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
        val baseUrlReady = Prefs.getBaseUrl(this).isNotBlank()
        val tokenReady = Prefs.getDeviceToken(this).isNotBlank()
        val deviceNameReady = Prefs.getDeviceName(this).isNotBlank()
        val notificationAccessReady = isNotificationListenerEnabled()
        val allowedCount = FilterRules.normalizePackages(Prefs.getAllowedPackages(this)).size
        val blockedCount = FilterRules.normalizePackages(Prefs.getBlockedPackages(this)).size
        val queueCount = NotificationQueueStore.getQueue(this).size
        val lines = mutableListOf(
            getString(R.string.child_setup_status_title),
            statusLine(Prefs.isChildRole(this), getString(R.string.child_setup_role_ready)),
            statusLine(baseUrlReady && tokenReady && deviceNameReady, getString(R.string.child_setup_pairing_ready)),
            statusLine(notificationAccessReady, getString(R.string.child_setup_notification_ready)),
            statusLine(allowedCount > 0 || blockedCount > 0, getString(R.string.child_setup_filters_ready, allowedCount, blockedCount)),
            statusLine(queueCount == 0, getString(R.string.child_setup_queue_ready, queueCount)),
            "",
            getString(R.string.child_setup_latest_status, Prefs.getLastStatus(this)),
        )
        return lines.joinToString("\n")
    }

    private fun statusLine(done: Boolean, label: String): String =
        "${if (done) "[OK]" else "[ ]"} $label"

    private fun isNotificationListenerEnabled(): Boolean {
        val enabledListeners = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
            ?: return false
        return enabledListeners.contains(packageName, ignoreCase = true)
    }

    private fun openWebPath(path: String) {
        val typedBaseUrl = baseUrlInput.text.toString().trim()
        if (typedBaseUrl.isNotBlank()) {
            Prefs.setBaseUrl(this, typedBaseUrl)
        }
        val baseUrl = Prefs.getBaseUrl(this).trim().trimEnd('/')
        if (baseUrl.isBlank()) {
            Toast.makeText(this, R.string.base_url_required, Toast.LENGTH_SHORT).show()
            return
        }
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("$baseUrl$path")))
    }

    private fun signInParent() {
        Prefs.setBaseUrl(this, baseUrlInput.text.toString().trim())
        val identifier = parentIdentifierInput.text.toString().trim()
        val password = parentPasswordInput.text.toString()
        if (identifier.isBlank() || password.isBlank()) {
            Toast.makeText(this, R.string.parent_login_required, Toast.LENGTH_SHORT).show()
            return
        }
        parentAlertSummaryText.text = getString(R.string.parent_signing_in)
        ParentApiClient.login(this, identifier, password) { ok, message ->
            runOnUiThread {
                parentPasswordInput.text?.clear()
                parentAlertSummaryText.text = message
                Toast.makeText(
                    this,
                    if (ok) R.string.parent_sign_in_ok else R.string.parent_sign_in_failed,
                    Toast.LENGTH_SHORT,
                ).show()
                if (ok) refreshParentAlerts()
            }
        }
    }

    private fun refreshParentAlerts() {
        parentAlertSummaryText.text = getString(R.string.parent_alerts_loading)
        ParentApiClient.fetchAlerts(this) { ok, message ->
            runOnUiThread {
                parentAlertSummaryText.text = message
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
        ParentApiClient.createChildDeviceLink(this, deviceName) { ok, message ->
            runOnUiThread {
                parentAlertSummaryText.text = message
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
        baseUrlInput.setText(uri.getQueryParameter("base_url").orEmpty())
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

    companion object {
        private const val SECTION_HOME = 0
        private const val SECTION_AUTH = 1
        private const val SECTION_QR = 2
        private const val SECTION_SETTINGS = 3
        private const val SECTION_CAPTURE = 4
        private const val SECTION_FILTERS = 5
        private const val SECTION_STATUS = 6
        private const val SECTION_LOGS = 7
    }
}
