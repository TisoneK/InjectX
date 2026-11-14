// Root build file. Plugin versions are declared here (apply false) and
// applied in each module. Pinned, known-good versions (ADR-10).
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.jvm") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "2.0.21" apply false
    // Kotlin 2.0+ requires the Compose Compiler Gradle plugin when compose is on.
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}
