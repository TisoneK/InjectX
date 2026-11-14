pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "injectx-android"

// `core` is a PURE Kotlin/JVM library (crypto + parsing + SNI logic) so it
// runs its golden-vector tests on a plain JDK — no Android SDK/emulator.
include(":core")

// `app` is the Android/Compose UI — the only module that needs the Android
// SDK. Include it only when an SDK is actually configured, so `:core` builds
// and tests on a bare JDK (no SDK) without failing AGP configuration.
val hasAndroidSdk = System.getenv("ANDROID_HOME") != null ||
    System.getenv("ANDROID_SDK_ROOT") != null ||
    file("local.properties").let { it.exists() && it.readText().contains("sdk.dir") }
if (hasAndroidSdk) {
    include(":app")
} else {
    gradle.rootProject {
        logger.lifecycle("[injectx] Android SDK not found — :app skipped (core-only build). Set ANDROID_HOME or add local.properties 'sdk.dir=' to include it.")
    }
}
