package com.injectx.core

import com.injectx.core.crypto.scheme.DarkI1
import com.injectx.core.crypto.scheme.EhiB2
import com.injectx.core.crypto.scheme.HcA5
import com.injectx.core.crypto.scheme.ZivH1
import com.injectx.core.detect.Detector
import com.injectx.core.model.Format
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import java.io.File

/**
 * Full pipeline — port of `backend/parser/parse_engine.py`:
 * detect → scheme decrypt → normalize into the canonical NormalizedConfig IR.
 * Output is a [JsonObject] matching the Python `NormalizedConfig.model_dump`
 * (all IR fields present, enums as values) minus `decrypt_trace`, which ADR-11
 * keeps out of the parity contract.
 */
object ParseEngine {

    // ── NormalizedConfig builder (map keyed by IR field name) ───────────────
    private class Norm(filepath: String, filename: String, format: Format) {
        val m = LinkedHashMap<String, JsonElement>()
        val warnings = ArrayList<String>()
        init {
            m["ir_version"] = JsonPrimitive("1.0")
            m["filepath"] = JsonPrimitive(filepath)
            m["filename"] = JsonPrimitive(filename)
            m["format"] = JsonPrimitive(format.jsonName())
        }
        fun setIfNull(key: String, v: JsonElement?) {
            if (key !in SETTABLE_FIELDS) return // mirrors Python hasattr(config, key)
            if (v == null || v is JsonNull) return
            val cur = m[key]
            if (cur == null || cur is JsonNull) m[key] = v
        }
        fun set(key: String, v: JsonElement?) { if (key in SETTABLE_FIELDS && v != null) m[key] = v }

        fun toJsonObject(
            isEncrypted: Boolean, status: String, scheme: String?, rawData: JsonElement?,
        ): JsonObject = buildJsonObject {
            val all = linkedMapOf<String, JsonElement>()
            // defaults
            all["ir_version"] = JsonPrimitive("1.0")
            all["is_encrypted"] = JsonPrimitive(isEncrypted)
            all["decryption_status"] = JsonPrimitive(status)
            all["scheme_used"] = scheme?.let { JsonPrimitive(it) } ?: JsonNull
            all["payload_parsed"] = JsonArray(emptyList())
            all["custom_headers"] = JsonObject(emptyMap())
            all["errors"] = JsonArray(emptyList())
            all["warnings"] = JsonArray(warnings.map { JsonPrimitive(it) })
            for (f in NULLABLE_FIELDS) all[f] = JsonNull
            // overlay what the normalizer set
            all.putAll(m)
            all["is_encrypted"] = JsonPrimitive(isEncrypted)
            all["decryption_status"] = JsonPrimitive(status)
            all["scheme_used"] = scheme?.let { JsonPrimitive(it) } ?: JsonNull
            all["warnings"] = JsonArray(warnings.map { JsonPrimitive(it) })
            all["raw_data"] = rawData ?: (m["raw_data"] ?: JsonNull)
            for ((k, v) in all) put(k, v)
        }
    }

    // Actual NormalizedConfig attributes the normalizers may set (mirrors
    // Python's hasattr guard — e.g. "notes"/"openvpn_config"/"ssh_host" are
    // NOT fields and get dropped).
    private val SETTABLE_FIELDS = setOf(
        "host", "port", "protocol", "ssh_server", "ssh_port", "ssh_user", "ssh_pass", "ssh_key",
        "proxy_host", "proxy_port", "payload", "sni", "bug_host", "dns", "remote_dns",
        "v2ray", "vmess_config", "vless_config", "websocket", "connection_type", "tunnel_type",
        "tunnel_mode", "inject_type", "tls_version", "internal_ip", "ssl_enabled",
        "hysteria", "xray", "shadowsocks", "wireguard", "custom_headers", "raw_data",
    )

    private val NULLABLE_FIELDS = listOf(
        "host", "port", "protocol", "ssh_server", "ssh_port", "ssh_user", "ssh_pass", "ssh_key",
        "proxy_host", "proxy_port", "payload", "sni", "bug_host", "dns", "remote_dns",
        "v2ray", "vmess_config", "vless_config", "websocket", "connection_type", "tunnel_type",
        "tunnel_mode", "inject_type", "tls_version", "internal_ip", "ssl_enabled",
        "hysteria", "xray", "shadowsocks", "wireguard", "raw_data", "decrypt_trace",
    )

    private fun Format.jsonName(): String = when (this) {
        Format.EHI -> "ehi"; Format.HC -> "hc"; Format.HAT -> "hat"; Format.DARK -> "dark"
        Format.DARKTUNNEL -> "darktunnel"; Format.TLS -> "tls"; Format.NPV -> "npv"; Format.NSH -> "nsh"
        Format.VHD -> "vhd"; Format.OVPN -> "ovpn"; Format.CONF -> "conf"; Format.ZIV -> "ziv"
        Format.LNK -> "lnk"; Format.ENCRYPTED_UNKNOWN -> "encrypted_unknown"; Format.UNKNOWN -> "unknown"
    }

    private fun prim(s: String?): JsonElement = s?.let { JsonPrimitive(it) } ?: JsonNull
    private fun str(e: JsonElement?): String? =
        when (e) { null, is JsonNull -> null; is JsonPrimitive -> e.content; else -> e.toString() }

    // ── universal field map (lowercased, - and space → _) ───────────────────
    private val FIELD_MAP = mapOf(
        "host" to "host", "server" to "host", "serveraddress" to "host", "server_address" to "host",
        "add" to "host", "address" to "host", "remotehost" to "host", "targethost" to "host",
        "sshserver" to "ssh_server", "ssh_server" to "ssh_server", "sshhost" to "ssh_host", "ssh_host" to "ssh_server",
        "port" to "port", "serverport" to "port", "server_port" to "port",
        "sshport" to "ssh_port", "ssh_port" to "ssh_port", "remoteport" to "port", "remote_port" to "port",
        "sshuser" to "ssh_user", "ssh_user" to "ssh_user", "username" to "ssh_user", "user" to "ssh_user",
        "login" to "ssh_user", "sshusername" to "ssh_user",
        "sshpass" to "ssh_pass", "ssh_pass" to "ssh_pass", "password" to "ssh_pass", "sshpassword" to "ssh_pass",
        "sshkey" to "ssh_key", "privatekey" to "ssh_key", "ssl_file" to "ssh_key",
        "proxyip" to "proxy_host", "proxy_ip" to "proxy_host", "proxyhost" to "proxy_host", "proxy_host" to "proxy_host",
        "proxyaddress" to "proxy_host", "proxyremoto" to "proxy_host", "proxyurl" to "proxy_host",
        "proxyport" to "proxy_port", "proxy_port" to "proxy_port", "proxyremotoporta" to "proxy_port",
        "payload" to "payload", "httppayload" to "payload", "custompayload" to "payload",
        "injectpayload" to "payload", "custom_payload" to "payload",
        "sni" to "sni", "servername" to "sni", "server_name" to "sni", "snivalue" to "sni",
        "snihostname" to "sni", "hostsnissl" to "sni", "customsni" to "sni", "adv_ssl_spoofhost" to "sni",
        "bughost" to "bug_host", "bug_host" to "bug_host", "customhost" to "bug_host", "custom_host" to "bug_host",
        "dns" to "dns", "dnsserver" to "dns", "dns_server" to "dns", "dnsresolver" to "dns", "primarydns" to "dns",
        "remotedns" to "remote_dns", "remote_dns" to "remote_dns", "dnsresolversecondary" to "remote_dns", "secondarydns" to "remote_dns",
        "connectiontype" to "connection_type", "tunneltype" to "tunnel_type", "connection_mode" to "connection_type",
        "tunnelmode" to "tunnel_mode", "injecttype" to "inject_type", "tunnel_type" to "tunnel_type",
        "ssl" to "ssl_enabled", "sslenabled" to "ssl_enabled", "tls" to "ssl_enabled",
    )
    private val IR_KEYS = setOf(
        "host", "ssh_server", "ssh_host", "port", "ssh_port", "ssh_user", "ssh_pass", "ssh_key",
        "proxy_host", "proxy_port", "payload", "sni", "bug_host", "dns", "remote_dns",
        "connection_type", "tunnel_type", "tunnel_mode", "inject_type", "ssl_enabled",
    )

    private fun applyFieldMap(raw: JsonObject): LinkedHashMap<String, JsonElement> {
        val result = LinkedHashMap<String, JsonElement>()
        val headers = LinkedHashMap<String, JsonElement>()
        for ((rawKey, value) in raw) {
            val kl = rawKey.lowercase().replace("-", "_").replace(" ", "_")
            val target = FIELD_MAP[kl]
            if (target != null) {
                if (result[target] == null || result[target] is JsonNull) result[target] = value
            } else if ("header" in kl) {
                if (value is JsonPrimitive && value.isString) headers[rawKey] = value
                else if (value is JsonObject) headers.putAll(value)
            }
        }
        if (headers.isNotEmpty()) result["custom_headers"] = JsonObject(headers)
        return result
    }

    private fun detectProtocol(data: JsonObject): String {
        val keys = data.keys.map { it.lowercase() }
        fun any(sub: String) = keys.any { sub in it }
        return when {
            any("v2ray") || any("vless") -> "v2ray"
            any("vmess") -> "vmess"
            any("hysteria") -> "hysteria"
            any("xray") -> "xray"
            any("shadowsocks") -> "shadowsocks"
            any("trojan") -> "trojan"
            any("ws") || keys.contains("websocket") -> "websocket"
            any("ssl") -> "ssl"
            any("ssh") -> "ssh"
            else -> "unknown"
        }
    }

    // ── json_data builders (scheme decrypt output → normalizer input) ───────
    private fun zivJsonData(fields: Map<String, String>): JsonObject {
        val fm = mapOf(
            "sshServer" to "ssh_server", "sshPort" to "ssh_port", "sshUser" to "ssh_user",
            "sshPass" to "ssh_pass", "proxyHost" to "proxy_host", "proxyPort" to "proxy_port",
            "sni" to "sni", "bugHost" to "bug_host", "payload" to "payload", "dnsServer" to "dns",
            "remoteDns" to "remote_dns", "notes" to "notes", "udpserver" to "host",
            "udpResolver" to "remote_dns", "sniHost" to "sni",
        )
        val out = LinkedHashMap<String, JsonElement>()
        for ((zk, ir) in fm) if (fields.containsKey(zk)) out[ir] = JsonPrimitive(fields[zk])
        val sshServer = (out["ssh_server"] as? JsonPrimitive)?.content
        if (sshServer != null) {
            if (":" in sshServer) {
                val p = sshServer.split(":")
                out.putIfAbsent("host", JsonPrimitive(p[0]))
                p.getOrNull(1)?.toIntOrNull()?.let { out.putIfAbsent("port", JsonPrimitive(it)) }
            } else out.putIfAbsent("host", JsonPrimitive(sshServer))
            out["protocol"] = JsonPrimitive("ssh")
        }
        out["_all_fields"] = JsonObject(fields.mapValues { JsonPrimitive(it.value) })
        return JsonObject(out)
    }

    private fun hcJsonData(r: HcA5.Result): JsonObject {
        val c = r.fields
        val out = LinkedHashMap<String, JsonElement>()
        fun cs(k: String): String? = (c[k] as? String) ?: (c[k] as? JsonPrimitive)?.content
        fun anyElem(k: String): JsonElement? = when (val v = c[k]) {
            null -> null; is JsonElement -> v; is String -> JsonPrimitive(v); else -> JsonPrimitive(v.toString())
        }
        cs("payload")?.let { out["payload"] = JsonPrimitive(it) }
        cs("proxy_host")?.let { proxy ->
            if (":" in proxy) { val i = proxy.lastIndexOf(':'); out["proxy_host"] = JsonPrimitive(proxy.substring(0, i))
                val p = proxy.substring(i + 1); out["proxy_port"] = p.toIntOrNull()?.let { JsonPrimitive(it) } ?: JsonPrimitive(p)
            } else out["proxy_host"] = JsonPrimitive(proxy)
        }
        cs("sni")?.let { out["sni"] = JsonPrimitive(it) }
        cs("ssh_server")?.let { ssh ->
            val m = Regex("^([\\w.\\-]+):(\\d+)@(.+):(.+)$").find(ssh)
            if (m != null) {
                out["ssh_server"] = JsonPrimitive(m.groupValues[1]); out["ssh_port"] = JsonPrimitive(m.groupValues[2].toInt())
                out["ssh_user"] = JsonPrimitive(m.groupValues[3]); out["ssh_pass"] = JsonPrimitive(m.groupValues[4])
                out["host"] = JsonPrimitive(m.groupValues[1]); out["port"] = JsonPrimitive(m.groupValues[2].toInt())
            } else { out["ssh_server"] = JsonPrimitive(ssh); out["host"] = JsonPrimitive(ssh) }
        }
        cs("openvpn_creds")?.let { creds -> if (":" in creds) { val u = creds.substringBefore(':'); val p = creds.substringAfter(':')
            out.putIfAbsent("ssh_user", JsonPrimitive(u)); out.putIfAbsent("ssh_pass", JsonPrimitive(p)) } }
        cs("notes")?.let { out["notes"] = JsonPrimitive(it) }
        anyElem("openvpn_config")?.let { out["openvpn_config"] = it }
        anyElem("v2ray_config")?.let { out["v2ray"] = it }
        cs("version")?.let { out["hc_version"] = JsonPrimitive(it) }
        cs("name")?.let { out["config_name"] = JsonPrimitive(it) }
        cs("connection_mode")?.let { out["connection_type"] = JsonPrimitive(it) }
        cs("dns_resolver")?.let { out["dns"] = JsonPrimitive(it) }
        anyElem("psiphon")?.let { out["psiphon"] = it }
        cs("slowdns_server")?.let { out["slowdns_server"] = JsonPrimitive(it) }
        cs("blocked_by_root")?.let { out["blocks_root"] = JsonPrimitive(it == "true") }
        cs("blocked_by_hwid")?.let { out["blocks_hwid"] = JsonPrimitive(it == "true") }
        cs("blocked_by_password")?.let { out["blocks_password"] = JsonPrimitive(it == "true") }
        cs("lock_all_config")?.let { out["locked"] = JsonPrimitive(it == "true") }
        cs("expiry_time")?.let { out["expiry"] = JsonPrimitive(it) }
        if (r.protections.isNotEmpty()) out["protections"] = JsonObject(r.protections.mapValues { JsonPrimitive(it.value) })
        out["_all_fields"] = JsonObject(c.mapValues { (_, v) -> when (v) { is JsonElement -> v; is String -> JsonPrimitive(v); null -> JsonNull; else -> JsonPrimitive(v.toString()) } })
        return JsonObject(out)
    }

    private fun ehiJsonData(cleaned: JsonObject): JsonObject {
        val fm = mapOf(
            "payload" to "payload", "remoteProxy" to "proxy_host", "sshServer" to "ssh_server",
            "sshPort" to "ssh_port", "sshUser" to "ssh_user", "sshPassword" to "ssh_pass",
            "sniHostname" to "sni", "customDns1" to "dns", "customDns2" to "remote_dns",
            "proxyURL" to "proxy_host", "proxyPort" to "proxy_port", "configMessage" to "notes",
            "v2rRawJson" to "v2ray",
        )
        val out = LinkedHashMap<String, JsonElement>()
        for ((ek, ir) in fm) {
            val v = cleaned[ek]
            if (v != null && v !is JsonNull && !(v is JsonPrimitive && v.isString && v.content.isEmpty())) {
                if (out[ir] == null) out[ir] = v
            }
        }
        (out["ssh_server"] as? JsonPrimitive)?.content?.let { ssh ->
            if (":" in ssh) { val p = ssh.split(":"); out.putIfAbsent("host", JsonPrimitive(p[0]))
                p.getOrNull(1)?.toIntOrNull()?.let { out.putIfAbsent("port", JsonPrimitive(it)) } }
        }
        val v2r = cleaned["v2rRawJson"]
        if (v2r is JsonObject) {
            out["v2ray"] = v2r
            (v2r["address"] as? JsonPrimitive)?.content?.let { out.putIfAbsent("host", JsonPrimitive(it)) }
            (v2r["port"] as? JsonPrimitive)?.content?.toIntOrNull()?.let { out.putIfAbsent("port", JsonPrimitive(it)) }
        } else if (v2r is JsonPrimitive && v2r.isString) out["v2ray_raw"] = v2r
        (cleaned["overwriteServerData"] as? JsonObject)?.let { out["overwrite_server"] = it }
        if (cleaned.containsKey("v2rRawJson") || cleaned.keys.any { it.startsWith("v2r") }) out["protocol"] = JsonPrimitive("v2ray")
        else if ((out["ssh_server"] as? JsonPrimitive)?.content?.isNotEmpty() == true) out["protocol"] = JsonPrimitive("ssh")
        out["_all_fields"] = cleaned
        return JsonObject(out)
    }

    private val METHODS = listOf("GET ", "POST ", "PUT ", "CONNECT ", "HEAD ", "OPTIONS ", "PATCH ")
    private fun parsePayload(payload: String): JsonArray {
        val headers = ArrayList<LinkedHashMap<String, JsonElement>>()
        var current = LinkedHashMap<String, JsonElement>()
        for (lineRaw in payload.trim().split("\n")) {
            val line = lineRaw.trim()
            if (line.isEmpty()) continue
            if (METHODS.any { line.startsWith(it) }) {
                if (current.isNotEmpty()) headers.add(current)
                val parts = line.split(Regex("\\s+"))
                current = LinkedHashMap()
                current["type"] = JsonPrimitive("method")
                current["method"] = JsonPrimitive(parts[0])
                current["path"] = JsonPrimitive(parts.getOrNull(1) ?: "/")
                current["version"] = JsonPrimitive(parts.getOrNull(2) ?: "HTTP/1.1")
            } else if (":" in line) {
                val key = line.substringBefore(":"); val value = line.substringAfter(":")
                if ((current["type"] as? JsonPrimitive)?.content != "method") { current = LinkedHashMap(); current["type"] = JsonPrimitive("header") }
                current[key.trim()] = JsonPrimitive(value.trim())
            }
        }
        if (current.isNotEmpty()) headers.add(current)
        return JsonArray(headers.map { JsonObject(it) })
    }

    // ── normalizers ─────────────────────────────────────────────────────────
    private fun normalizeZiv(n: Norm, data: JsonObject) {
        for (f in listOf("host", "port", "ssh_server", "ssh_port", "ssh_user", "ssh_pass",
            "proxy_host", "proxy_port", "sni", "bug_host", "payload", "dns", "remote_dns")) {
            n.setIfNull(f, data[f])
        }
        val proto = str(data["protocol"])
        n.m["protocol"] = JsonPrimitive(proto ?: if (str(data["ssh_server"]) != null) "ssh" else "unknown")
        data["_all_fields"]?.let { n.m["raw_data"] = buildJsonObject { put("_all_fields", it) } }
    }

    private fun normalizeDark(n: Norm, data: JsonObject) {
        val darkType = (str(data["type"]) ?: "").uppercase()
        val proto = mapOf("VLESS" to "vless", "VMESS" to "vmess", "TROJAN" to "trojan", "SSH" to "ssh",
            "SHADOWSOCKS" to "shadowsocks", "HYSTERIA" to "hysteria", "XRAY" to "xray")[darkType] ?: "unknown"
        n.m["protocol"] = JsonPrimitive(proto)
        val locked = data["encryptedLockedConfig"].let { it != null && it !is JsonNull && !(it is JsonPrimitive && it.isString && it.content.isEmpty()) }
        val filtered = JsonObject(data.filterKeys { it != "encryptedLockedConfig" })
        for ((k, v) in applyFieldMap(filtered)) if (v !is JsonObject && v !is JsonArray) n.setIfNull(k, v)
        var transport: String? = null
        for (sub in listOf("trojanTunnelConfig", "vlessTunnelConfig", "vmessTunnelConfig")) {
            val s = data[sub] as? JsonObject ?: continue
            val v2 = s["v2rayConfig"] as? JsonObject ?: continue
            (v2["transportNetwork"] as? JsonPrimitive)?.content?.let { transport = it; n.setIfNull("connection_type", JsonPrimitive(it)) }
        }
        n.m["raw_data"] = buildJsonObject {
            put("name", data["name"] ?: JsonNull); put("type", data["type"] ?: JsonNull)
            put("locked", JsonPrimitive(locked)); put("transport", transport?.let { JsonPrimitive(it) } ?: JsonNull)
        }
        if (locked) n.warnings.add(
            "This DARK Tunnel config is LOCKED by its author: the server/credentials are sealed in an encrypted 'encryptedLockedConfig' blob with a key that is not in the file, so only type and name are recoverable."
        )
    }

    private fun normalizeHc(n: Norm, data: JsonObject) {
        for ((k, v) in applyFieldMap(data)) if (k in IR_KEYS || k == "custom_headers") n.setIfNull(k, v)
        for (f in listOf("host", "port", "ssh_server", "ssh_port", "ssh_user", "ssh_pass",
            "proxy_host", "proxy_port", "sni", "payload", "notes", "openvpn_config", "v2ray", "connection_type", "dns")) {
            n.setIfNull(f, data[f])
        }
        if (n.m["protocol"] == null) {
            var proto = detectProtocol(data)
            val payload = str(n.m["payload"])
            if (proto == "unknown" && payload != null) {
                val pl = payload.lowercase()
                proto = when { "websocket" in pl -> "websocket"; "ssl" in pl || "tls" in pl -> "ssl"
                    str(n.m["ssh_server"]) != null -> "ssh"; else -> "unknown" }
            }
            n.m["protocol"] = JsonPrimitive(proto)
        }
        val extras = LinkedHashMap<String, JsonElement>()
        for (k in listOf("protections", "config_name", "hc_version", "expiry", "blocks_root", "blocks_hwid",
            "blocks_password", "locked", "psiphon", "slowdns_server", "_all_fields")) data[k]?.let { extras[k] = it }
        if (extras.isNotEmpty()) n.m["raw_data"] = JsonObject(extras)
    }

    private fun normalizeEhi(n: Norm, data: JsonObject) {
        val v2Fields = listOf("host", "port", "ssh_server", "ssh_port", "ssh_user", "ssh_pass",
            "proxy_host", "proxy_port", "sni", "payload", "notes", "v2ray", "dns", "remote_dns", "protocol")
        if (v2Fields.any { data.containsKey(it) }) {
            for (f in v2Fields) if (f != "protocol") n.setIfNull(f, data[f])
            str(data["protocol"])?.let { n.m["protocol"] = JsonPrimitive(it) }
            val extras = LinkedHashMap<String, JsonElement>()
            for (k in listOf("_all_fields", "overwrite_server", "v2ray_raw")) data[k]?.let { extras[k] = it }
            if (extras.isNotEmpty()) n.m["raw_data"] = JsonObject(extras)
        } else {
            for ((k, v) in applyFieldMap(data)) n.setIfNull(k, v)
            if (n.m["protocol"] == null) n.m["protocol"] = JsonPrimitive(detectProtocol(data))
        }
    }

    // ── pipeline ─────────────────────────────────────────────────────────────
    fun parseConfig(file: File): JsonObject = parseConfig(file.readBytes(), file.name, file.path)

    /** Bytes-based entry — for Android SAF (Uri → bytes + display name). */
    fun parseConfig(raw: ByteArray, filename: String, filepath: String = filename): JsonObject {
        val det = Detector.detect(raw, filename, filepath)
        val fmt = det.format

        var jsonData: JsonObject? = null
        var status = "not_encrypted"
        var scheme: String? = null

        when (fmt) {
            Format.ZIV -> { val r = ZivH1.decrypt(raw); scheme = "H1"
                if (r.success) { jsonData = zivJsonData(r.fields); status = "success" } else status = "failed" }
            Format.DARK, Format.DARKTUNNEL -> { val r = DarkI1.decrypt(raw); scheme = "I1"
                when (r.status) { DarkI1.Status.SUCCESS -> { jsonData = r.envelope; status = "success" }
                    DarkI1.Status.PARTIAL -> { jsonData = r.envelope; status = "partial" }
                    DarkI1.Status.FAILED -> status = "failed" } }
            Format.HC -> { val r = HcA5.decrypt(raw); scheme = "A5"
                if (r.success) { jsonData = hcJsonData(r); status = "success" } else status = "failed" }
            Format.EHI -> { val r = EhiB2.decrypt(raw)
                if (r.success) { jsonData = ehiJsonData(r.fields); status = "success"; scheme = "B2" } else { status = "failed"; scheme = "B2" } }
            Format.TLS -> { scheme = "F1"; status = "failed" } // F1 decryptor fails (rotated key); not ported
            else -> status = "no_decryptor"
        }

        val n = Norm(det.filepath, det.filename, fmt)
        var rawData: JsonElement? = null
        if (jsonData != null) {
            when (fmt) {
                Format.ZIV -> normalizeZiv(n, jsonData)
                Format.DARK, Format.DARKTUNNEL -> normalizeDark(n, jsonData)
                Format.HC -> normalizeHc(n, jsonData)
                Format.EHI -> normalizeEhi(n, jsonData)
                else -> {}
            }
            val payload = str(n.m["payload"])
            if (!payload.isNullOrEmpty()) n.m["payload_parsed"] = parsePayload(payload)
        }
        // failed / no-decryptor raw_data (only when the normalizer set none)
        if ((status == "failed" || status == "no_decryptor") && n.m["raw_data"] == null) {
            val f = det.features
            rawData = buildJsonObject {
                put("file_size", JsonPrimitive(raw.size))
                put("hex_preview", JsonPrimitive(raw.copyOfRange(0, minOf(64, raw.size)).joinToString("") { "%02x".format(it.toInt() and 0xff) }))
                put("features", buildJsonObject {
                    put("entropy", JsonPrimitive(f.entropy)); put("byte_distribution_skew", JsonPrimitive(f.byteDistributionSkew))
                    put("ascii_ratio", JsonPrimitive(f.asciiRatio)); put("is_zip", JsonPrimitive(f.isZip))
                    put("base64_likelihood", JsonPrimitive(f.base64Likelihood)); put("null_byte_ratio", JsonPrimitive(f.nullByteRatio))
                })
            }
        }
        return n.toJsonObject(det.isEncrypted, status, scheme, rawData)
    }
}
