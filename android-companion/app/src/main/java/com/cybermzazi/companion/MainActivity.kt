package com.cybermzazi.companion

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var baseUrlInput: EditText
    private lateinit var tokenInput: EditText
    private lateinit var deviceNameInput: EditText
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        baseUrlInput = findViewById(R.id.baseUrlInput)
        tokenInput = findViewById(R.id.tokenInput)
        deviceNameInput = findViewById(R.id.deviceNameInput)
        statusText = findViewById(R.id.statusText)

        findViewById<Button>(R.id.saveButton).setOnClickListener {
            saveSettings()
        }
        findViewById<Button>(R.id.notificationAccessButton).setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        findViewById<Button>(R.id.sendTestButton).setOnClickListener {
            sendTestPayload()
        }

        populateFields()
    }

    override fun onResume() {
        super.onResume()
        populateFields()
    }

    private fun populateFields() {
        baseUrlInput.setText(Prefs.getBaseUrl(this))
        tokenInput.setText(Prefs.getDeviceToken(this))
        deviceNameInput.setText(Prefs.getDeviceName(this))
        statusText.text = Prefs.getLastStatus(this)
    }

    private fun saveSettings() {
        Prefs.setBaseUrl(this, baseUrlInput.text.toString().trim())
        Prefs.setDeviceToken(this, tokenInput.text.toString().trim())
        Prefs.setDeviceName(this, deviceNameInput.text.toString().trim())
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
                Toast.makeText(
                    this,
                    if (ok) R.string.test_sent_ok else R.string.test_sent_failed,
                    Toast.LENGTH_SHORT,
                ).show()
            }
        }
    }
}
