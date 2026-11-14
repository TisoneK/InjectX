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
// `app` is the Android/Compose UI and is the only module that needs the SDK.
include(":core")
include(":app")
