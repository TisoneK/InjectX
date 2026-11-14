package com.injectx.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

/**
 * Faithful Kotlin port of `backend/ir/models.py` (IR v1.0) — the canonical
 * contract every layer produces/consumes. Enum serial names match the Python
 * enum *values* (the backend dumps with `use_enum_values=True`), so these
 * deserialize the golden fixtures directly.
 *
 * NOTE: this file is a mechanical port written WITHOUT a Kotlin compiler on
 * the authoring host (no JDK/Gradle). It is expected to compile, but the first
 * toolchain-equipped session should build `:core` and reconcile any annotation
 * nits before relying on it. See android/README.md.
 */

const val IR_VERSION = "1.0"

@Serializable
enum class Format {
    @SerialName("ehi") EHI,
    @SerialName("hc") HC,
    @SerialName("hat") HAT,
    @SerialName("dark") DARK,
    @SerialName("darktunnel") DARKTUNNEL,
    @SerialName("tls") TLS,
    @SerialName("npv") NPV,
    @SerialName("nsh") NSH,
    @SerialName("vhd") VHD,
    @SerialName("ovpn") OVPN,
    @SerialName("conf") CONF,
    @SerialName("ziv") ZIV,
    @SerialName("lnk") LNK,
    @SerialName("encrypted_unknown") ENCRYPTED_UNKNOWN,
    @SerialName("unknown") UNKNOWN,
}

@Serializable
enum class Protocol {
    @SerialName("ssh") SSH,
    @SerialName("ssl") SSL,
    @SerialName("v2ray") V2RAY,
    @SerialName("vless") VLESS,
    @SerialName("vmess") VMESS,
    @SerialName("websocket") WEBSOCKET,
    @SerialName("hysteria") HYSTERIA,
    @SerialName("hysteria2") HYSTERIA2,
    @SerialName("xray") XRAY,
    @SerialName("shadowsocks") SHADOWSOCKS,
    @SerialName("trojan") TROJAN,
    @SerialName("wireguard") WIREGUARD,
    @SerialName("tls_vpn") TLS_VPN,
    @SerialName("socks") SOCKS,
    @SerialName("slowdns") SLOWDNS,
    @SerialName("dnstt") DNSTT,
    @SerialName("unknown") UNKNOWN,
}

@Serializable
enum class DecryptStatus {
    @SerialName("success") SUCCESS,
    @SerialName("partial") PARTIAL,
    @SerialName("failed") FAILED,
    @SerialName("not_encrypted") NOT_ENCRYPTED,
    @SerialName("no_decryptor") NO_DECRYPTOR,
}

@Serializable
enum class Scheme {
    A1, A2, A3, A4, A5,
    B1, B2,
    C1, D1, E1, F1, G1, H1, I1,
    @SerialName("none") NONE,
    @SerialName("unsupported") UNSUPPORTED,
}

@Serializable
data class DecryptAttempt(
    val scheme: Scheme,
    @SerialName("key_label") val keyLabel: String = "",
    val result: String,
    val confidence: Double = 0.0,
    @SerialName("error_message") val errorMessage: String = "",
)

@Serializable
data class DecryptTrace(
    val filepath: String = "",
    val filename: String = "",
    val format: Format = Format.UNKNOWN,
    val attempts: List<DecryptAttempt> = emptyList(),
    @SerialName("winning_scheme") val winningScheme: Scheme? = null,
    @SerialName("winning_key_label") val winningKeyLabel: String? = null,
)

/**
 * The canonical normalized config — the exact shape every parser must produce
 * and the UI renders. Arbitrary nested JSON fields (v2ray, custom_headers, …)
 * are kept as [JsonElement]/[JsonObject] rather than typed classes, matching
 * the Python `dict[str, Any]`.
 */
@Serializable
data class NormalizedConfig(
    @SerialName("ir_version") val irVersion: String = IR_VERSION,
    val filepath: String,
    val filename: String,
    val format: Format,
    @SerialName("is_encrypted") val isEncrypted: Boolean = false,
    @SerialName("decryption_status") val decryptionStatus: DecryptStatus = DecryptStatus.NOT_ENCRYPTED,
    @SerialName("scheme_used") val schemeUsed: Scheme? = null,

    val host: String? = null,
    val port: Int? = null,
    val protocol: Protocol? = null,

    @SerialName("ssh_server") val sshServer: String? = null,
    @SerialName("ssh_port") val sshPort: Int? = null,
    @SerialName("ssh_user") val sshUser: String? = null,
    @SerialName("ssh_pass") val sshPass: String? = null,
    @SerialName("ssh_key") val sshKey: String? = null,

    @SerialName("proxy_host") val proxyHost: String? = null,
    @SerialName("proxy_port") val proxyPort: Int? = null,

    val payload: String? = null,
    @SerialName("payload_parsed") val payloadParsed: List<JsonElement> = emptyList(),
    @SerialName("custom_headers") val customHeaders: JsonObject? = null,
    val sni: String? = null,
    @SerialName("bug_host") val bugHost: String? = null,

    val dns: String? = null,
    @SerialName("remote_dns") val remoteDns: String? = null,

    val v2ray: JsonObject? = null,
    @SerialName("vmess_config") val vmessConfig: JsonObject? = null,
    @SerialName("vless_config") val vlessConfig: JsonObject? = null,
    val websocket: JsonObject? = null,

    @SerialName("connection_type") val connectionType: String? = null,
    @SerialName("tunnel_type") val tunnelType: String? = null,
    @SerialName("tunnel_mode") val tunnelMode: String? = null,
    @SerialName("inject_type") val injectType: String? = null,

    @SerialName("tls_version") val tlsVersion: String? = null,
    @SerialName("internal_ip") val internalIp: String? = null,
    @SerialName("ssl_enabled") val sslEnabled: Boolean? = null,

    val hysteria: JsonObject? = null,
    val xray: JsonObject? = null,
    val shadowsocks: JsonObject? = null,
    val wireguard: JsonObject? = null,

    val errors: List<String> = emptyList(),
    val warnings: List<String> = emptyList(),
    @SerialName("raw_data") val rawData: JsonObject? = null,

    @SerialName("decrypt_trace") val decryptTrace: DecryptTrace? = null,
)
