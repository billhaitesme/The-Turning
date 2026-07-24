package arc.omega.bridgezero

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

@Suppress("DEPRECATION")
class SecureStore(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    // Required by the Epoch IX brief. Isolated here because AndroidX deprecated
    // this API; it can be replaced without changing networking or UI state.
    private val secrets: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "bridge_zero_credentials",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )
    private val settings = context.getSharedPreferences("bridge_zero_settings", Context.MODE_PRIVATE)

    fun token(): String? = secrets.getString("bearer_token", null)
    fun server(): String = settings.getString("server_url", "") ?: ""

    fun save(server: String, token: String) {
        secrets.edit().putString("bearer_token", token).apply()
        settings.edit().putString("server_url", server).apply()
    }

    fun clear() {
        secrets.edit().clear().apply()
        settings.edit().remove("server_url").apply()
    }
}
