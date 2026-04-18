package com.cybermzazi.companion

import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout

class MainActivity : AppCompatActivity() {

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var menuToggle: TextView

    private lateinit var pairingSection: View
    private lateinit var actionsSection: View
    private lateinit var filtersSection: View
    private lateinit var statusSection: View
    private lateinit var logSection: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        drawerLayout = findViewById(R.id.drawerLayout)
        menuToggle = findViewById(R.id.menuToggle)

        pairingSection = findViewById(R.id.pairingSection)
        actionsSection = findViewById(R.id.actionsSection)
        filtersSection = findViewById(R.id.filtersSection)
        statusSection = findViewById(R.id.statusSection)
        logSection = findViewById(R.id.logSection)

        // Toggle sidebar
        menuToggle.setOnClickListener {
            if (drawerLayout.isDrawerOpen(GravityCompat.START)) {
                drawerLayout.closeDrawer(GravityCompat.START)
            } else {
                drawerLayout.openDrawer(GravityCompat.START)
            }
        }

        // Sidebar clicks
        findViewById<TextView>(R.id.menuHome).setOnClickListener { showSection(0) }
        findViewById<TextView>(R.id.menuCapture).setOnClickListener { showSection(1) }
        findViewById<TextView>(R.id.menuFilters).setOnClickListener { showSection(2) }
        findViewById<TextView>(R.id.menuStatus).setOnClickListener { showSection(3) }
        findViewById<TextView>(R.id.menuLog).setOnClickListener { showSection(4) }

        showSection(0)
    }

    private fun showSection(position: Int) {
        pairingSection.visibility = if (position == 0) View.VISIBLE else View.GONE
        actionsSection.visibility = if (position == 1) View.VISIBLE else View.GONE
        filtersSection.visibility = if (position == 2) View.VISIBLE else View.GONE
        statusSection.visibility = if (position == 3) View.VISIBLE else View.GONE
        logSection.visibility = if (position == 4) View.VISIBLE else View.GONE

        drawerLayout.closeDrawer(GravityCompat.START)
    }
}