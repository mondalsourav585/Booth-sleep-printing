import os, shutil

dirs = [
    "app/src/main/assets",
    "app/src/main/res/xml",
    "app/src/main/res/values",
    "app/src/main/res/drawable",
    "app/src/main/java/com/krishnanagar/slipprinter",
]
for d in dirs:
    os.makedirs(d, exist_ok=True)

for cand in ["index.html", "voter_slip_printer.html"]:
    if os.path.exists(cand):
        shutil.copyfile(cand, "app/src/main/assets/index.html")
        break

files = {
    "settings.gradle.kts": """pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "VoterSlipPrinter"
include(":app")
""",
    "build.gradle.kts": """plugins {
    id("com.android.application") version "8.7.2" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
}
""",
    "gradle.properties": """org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
""",
    "app/build.gradle.kts": """plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.krishnanagar.slipprinter"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.krishnanagar.slipprinter"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
}
""",
    "app/src/main/res/values/strings.xml": """<?xml version="1.0" encoding="utf-8"?>
<resources><string name="app_name">ভোটার স্লিপ প্রিন্টার</string></resources>
""",
    "app/src/main/res/values/themes.xml": """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.SlipPrinter" parent="Theme.AppCompat.Light.NoActionBar">
        <item name="colorPrimary">#1b365d</item>
        <item name="colorPrimaryDark">#0f223d</item>
        <item name="colorAccent">#0d9488</item>
        <item name="android:statusBarColor">#0f223d</item>
        <item name="android:navigationBarColor">#ffffff</item>
        <item name="android:windowLightStatusBar">false</item>
        <item name="android:fitsSystemWindows">true</item>
    </style>
</resources>
""",
    "app/src/main/res/xml/file_paths.xml": """<?xml version="1.0" encoding="utf-8"?>
<paths><cache-path name="exports" path="exports/" /></paths>
""",
    "app/src/main/res/drawable/ic_launcher_printer.xml": """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#1b365d" android:pathData="M0,0h108v108h-108z" />
    <path android:fillColor="#ffffff" android:pathData="M34,26h40v18h-40z" />
    <path android:fillColor="#0d9488" android:pathData="M24,44h60v26h-60z" />
    <path android:fillColor="#ffffff" android:pathData="M34,58h40v24h-40z" />
</vector>
""",
    "app/src/main/AndroidManifest.xml": """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />
    <application
        android:allowBackup="true"
        android:icon="@drawable/ic_launcher_printer"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.SlipPrinter">
        <activity android:name=".MainActivity" android:exported="true" android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <provider android:name="androidx.core.content.FileProvider" android:authorities="${applicationId}.fileprovider" android:exported="false" android:grantUriPermissions="true">
            <meta-data android:name="android.support.FILE_PROVIDER_PATHS" android:resource="@xml/file_paths" />
        </provider>
    </application>
</manifest>
""",
    "app/src/main/java/com/krishnanagar/slipprinter/MainActivity.kt": r"""package com.krishnanagar.slipprinter

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.*
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Base64
import android.view.ViewGroup
import android.webkit.*
import android.widget.FrameLayout
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.UUID

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private val fileChooser = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        filePathCallback?.onReceiveValue(if (uri != null) arrayOf(uri) else null)
        filePathCallback = null
    }
    private val btPerm = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val req = listOf(Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN)
                .filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
            if (req.isNotEmpty()) btPerm.launch(req.toTypedArray())
        }
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.parseColor("#0f223d"))
            fitsSystemWindows = true
            layoutParams = ViewGroup.LayoutParams(-1, -1)
        }
        webView = WebView(this).apply { layoutParams = FrameLayout.LayoutParams(-1, -1) }
        root.addView(webView)
        setContentView(root)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            cacheMode = WebSettings.LOAD_NO_CACHE
            blockNetworkLoads = true
        }
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(v: WebView?, cb: ValueCallback<Array<Uri>>?, p: FileChooserParams?): Boolean {
                filePathCallback?.onReceiveValue(null)
                filePathCallback = cb
                fileChooser.launch("*/*")
                return true
            }
        }
        webView.addJavascriptInterface(AndroidPrinterBridge(), "AndroidPrinter")
        webView.loadUrl("file:///android_asset/index.html")
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack() else finish()
            }
        })
    }

    inner class AndroidPrinterBridge {
        private val sppUuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

        @SuppressLint("MissingPermission")
        @JavascriptInterface
        fun getPairedPrinters(): String {
            val arr = JSONArray()
            try {
                val adapter = (getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
                if (adapter != null && adapter.isEnabled) {
                    adapter.bondedDevices?.forEach { d ->
                        arr.put(JSONObject().put("name", d.name ?: "Bluetooth").put("address", d.address))
                    }
                }
            } catch (e: Exception) { e.printStackTrace() }
            return arr.toString()
        }

        @SuppressLint("MissingPermission")
        @JavascriptInterface
        fun printBase64Png(address: String, base64Png: String, targetWidth: Int): String {
            return try {
                val adapter = (getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter ?: return "Bluetooth নেই"
                if (!adapter.isEnabled) return "Bluetooth চালু করুন"
                val raw = Base64.decode(base64Png, Base64.DEFAULT)
                val orig = BitmapFactory.decodeByteArray(raw, 0, raw.size) ?: return "ইমেজ এরর"
                val w = if (targetWidth == 576) 576 else 384
                val h = (orig.height * w) / orig.width
                val bmp = Bitmap.createScaledBitmap(orig, w, h, true)
                val socket = adapter.getRemoteDevice(address).createRfcommSocketToServiceRecord(sppUuid)
                adapter.cancelDiscovery()
                socket.connect()
                val out = socket.outputStream
                out.write(byteArrayOf(0x1B, 0x40))
                out.flush()
                val wb = w / 8
                var y0 = 0
                while (y0 < h) {
                    val sh = minOf(128, h - y0)
                    val buf = ByteArrayOutputStream()
                    buf.write(byteArrayOf(0x1D, 0x76, 0x30, 0x00, (wb and 255).toByte(), (wb shr 8).toByte(), (sh and 255).toByte(), (sh shr 8).toByte()))
                    for (y in y0 until y0 + sh) {
                        for (xb in 0 until wb) {
                            var b = 0
                            for (bit in 0..7) {
                                val px = bmp.getPixel(xb * 8 + bit, y)
                                if ((Color.red(px) * 30 + Color.green(px) * 59 + Color.blue(px) * 11) / 100 < 160) b = b or (1 shl (7 - bit))
                            }
                            buf.write(b)
                        }
                    }
                    out.write(buf.toByteArray())
                    out.flush()
                    Thread.sleep(35)
                    y0 += sh
                }
                out.write(byteArrayOf(0x0A, 0x0A, 0x0A))
                out.flush()
                Thread.sleep(150)
                socket.close()
                "OK"
            } catch (e: Exception) { e.message ?: "Bluetooth ব্যর্থ" }
        }

        @JavascriptInterface
        fun shareBase64Png(filename: String, base64Png: String) {
            runOnUiThread {
                try {
                    val dir = File(cacheDir, "exports").apply { mkdirs() }
                    val f = File(dir, filename.replace(Regex("[^a-zA-Z0-9._-]"), "_")).apply { writeBytes(Base64.decode(base64Png, Base64.DEFAULT)) }
                    val uri = FileProvider.getUriForFile(this@MainActivity, "${applicationContext.packageName}.fileprovider", f)
                    startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                        type = "image/png"
                        putExtra(Intent.EXTRA_STREAM, uri)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }, "স্লিপ ইমেজ শেয়ার করুন"))
                } catch (e: Exception) { e.printStackTrace() }
            }
        }
    }
}
""",
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)

print("Android project generated cleanly.")
