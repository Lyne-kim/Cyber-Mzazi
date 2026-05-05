package com.cybermzazi.companion

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
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
    private lateinit var allowedPackagesInput: EditText
    private lateinit var blockedPackagesInput: EditText
    private lateinit var statusText: TextView
    private lateinit var recentLogText: TextView

    private lateinit var menuHome: TextView
    private lateinit var menuCapture: TextView
    private lateinit var menuFilters: TextView
    private lateinit var menuStatus: TextView
    private lateinit var menuLog: TextView

    private lateinit var roleSection: View
    private lateinit var pairingSection: View
    private lateinit var actionsSection: View
    private lateinit var filtersSection: View
    private lateinit var statusSection: View
    private lateinit var logSection: View

    private var currentSection = 0

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
        allowedPackagesInput = findViewById(R.id.allowedPackagesInput)
        blockedPackagesInput = findViewById(R.id.blockedPackagesInput)
        statusText = findViewById(R.id.statusText)
        recentLogText = findViewById(R.id.recentLogText)

        menuHome = findViewById(R.id.menuHome)
        menuCapture = findViewById(R.id.menuCapture)
        menuFilters = findViewById(R.id.menuFilters)
        menuStatus = findViewById(R.id.menuStatus)
        menuLog = findViewById(R.id.menuLog)

        roleSection = findViewById(R.id.roleSection)
        pairingSection = findViewById(R.id.pairingSection)
        actionsSection = findViewById(R.id.actionsSection)
        filtersSection = findViewById(R.id.filtersSection)
        statusSection = findViewById(R.id.statusSection)
        logSection = findViewById(R.id.logSection)

        menuToggle.setOnClickListener {
            if (drawerLayout.isDrawerOpen(GravityCompat.START)) {
                drawerLayout.closeDrawer(GravityCompat.START)
            } else {
                drawerLayout.openDrawer(GravityCompat.START)
            }
        }

        menuHome.setOnClickListener { showSection(0) }
        menuCapture.setOnClickListener { showSection(1) }
        menuFilters.setOnClickListener { showSection(2) }
        menuStatus.setOnClickListener { showSection(3) }
        menuLog.setOnClickListener { showSection(4) }

        parentRoleButton.setOnClickListener { setDeviceRole(Prefs.ROLE_PARENT) }
        childRoleButton.setOnClickListener { setDeviceRole(Prefs.ROLE_CHILD) }

        findViewById<Button>(R.id.saveButton).setOnClickListener {
            saveSettings()
        }
        findViewById<Button>(R.id.scanQrButton).setOnClickListener {
            startQrPairing()
        }
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

        populateFields()
        updateRoleUi()
        showSection(0)
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
                }
            }
        }
    }

    private fun populateFields() {
        baseUrlInput.setText(Prefs.getBaseUrl(this))
        tokenInput.setText(Prefs.getDeviceToken(this))
        deviceNameInput.setText(Prefs.getDeviceName(this))
        allowedPackagesInput.setText(Prefs.getAllowedPackages(this))
        blockedPackagesInput.setText(Prefs.getBlockedPackages(this))
        statusText.text = Prefs.getLastStatus(this)
        recentLogText.text = RecentNotificationLog.render(this)
    }

    private fun updateRoleUi() {
        val isChildRole = Prefs.isChildRole(this)
        roleBadge.text = getString(if (isChildRole) R.string.role_child else R.string.role_parent)
        roleSummaryText.text = getString(if (isChildRole) R.string.role_child_copy else R.string.role_parent_copy)
        captureRoleHint.text = getString(if (isChildRole) R.string.actions_section_copy else R.string.parent_mode_capture_disabled)

        setRoleButtonState(parentRoleButton, !isChildRole)
        setRoleButtonState(childRoleButton, isChildRole)

        menuCapture.visibility = if (isChildRole) View.VISIBLE else View.GONE
        menuFilters.visibility = if (isChildRole) View.VISIBLE else View.GONE

        if (!isChildRole && (currentSection == 1 || currentSection == 2)) {
            currentSection = 0
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
        val resolvedPosition = if (!Prefs.isChildRole(this) && (position == 1 || position == 2)) 0 else position
        currentSection = resolvedPosition

        roleSection.visibility = if (resolvedPosition == 0) View.VISIBLE else View.GONE
        pairingSection.visibility = if (resolvedPosition == 0) View.VISIBLE else View.GONE
        actionsSection.visibility = if (resolvedPosition == 1 && Prefs.isChildRole(this)) View.VISIBLE else View.GONE
        filtersSection.visibility = if (resolvedPosition == 2 && Prefs.isChildRole(this)) View.VISIBLE else View.GONE
        statusSection.visibility = if (resolvedPosition == 3) View.VISIBLE else View.GONE
        logSection.visibility = if (resolvedPosition == 4) View.VISIBLE else View.GONE
        syncDrawerState(resolvedPosition)
        drawerLayout.closeDrawer(GravityCompat.START)
    }

    private fun syncDrawerState(position: Int) {
        updateDrawerItem(menuHome, position == 0)
        updateDrawerItem(menuCapture, position == 1)
        updateDrawerItem(menuFilters, position == 2)
        updateDrawerItem(menuStatus, position == 3)
        updateDrawerItem(menuLog, position == 4)
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

    private fun sendTestPayload() {
        saveSettings()
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
}
