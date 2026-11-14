// core — pure Kotlin/JVM library: format detection, the 13 decrypt schemes,
// the parse engine, and SNI Hunter logic. No Android dependencies, so its
// unit + golden-vector tests run on any JDK 17 (`:core:test`), no emulator.
plugins {
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.kotlin.plugin.serialization")
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    // ChaCha20 (pre-API-28 parity) and Argon2id — the two primitives the JDK
    // lacks. One dependency covers both (ADR-10 §crypto).
    implementation("org.bouncycastle:bcprov-jdk18on:1.78.1")
    // Normalized-config (de)serialization + loading golden fixtures in tests.
    // `api`: JsonObject appears in ParseEngine's public return type, so :app
    // needs it transitively.
    api("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    // SNI Hunter networking (Phase 7).
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("dnsjava:dnsjava:3.6.1")

    testImplementation("junit:junit:4.13.2")
}

// The golden fixtures live outside the module (shared with the Python
// generator), so expose them to tests as a resource root.
sourceSets {
    named("test") {
        resources.srcDir("$rootDir/goldens/fixtures")
    }
}
