package arc.omega.bridgezero

import com.google.gson.Gson
import com.google.gson.JsonParser
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.ResponseBody
import retrofit2.Call
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Headers
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Streaming
import java.net.URI

interface RuntimeService {
    @GET("api/mobile/v1/compatibility") suspend fun compatibility(): Compatibility
    @GET("api/mobile/v1/status") suspend fun status(): RuntimeStatus
    @GET("api/mobile/v1/telemetry") suspend fun telemetry(): RuntimeTelemetry
    @GET("api/mobile/v1/diagnostics") suspend fun diagnostics(): Diagnostics
    @GET("api/mobile/v1/conversations/active") suspend fun activeConversation(): Conversation
    @GET("api/mobile/v1/conversations/{id}") suspend fun conversation(@Path("id") id: String): Conversation
    @POST("api/mobile/v1/conversations") suspend fun createConversation(@Body request: ConversationRequest): Conversation
    @GET("api/mobile/v1/chronicle") suspend fun chronicle(): List<ChronicleEntry>

    @Streaming
    @Headers("Accept: text/event-stream")
    @GET("api/mobile/v1/events")
    fun runtimeEvents(): Call<ResponseBody>

    @Streaming
    @POST("api/mobile/v1/conversations/{id}/messages")
    fun streamMessage(@Path("id") id: String, @Body request: MessageRequest): Call<ResponseBody>
}

class RuntimeApi private constructor(private val service: RuntimeService) {
    suspend fun compatibility() = service.compatibility()
    suspend fun status() = service.status()
    suspend fun telemetry() = service.telemetry()
    suspend fun diagnostics() = service.diagnostics()
    suspend fun activeConversation() = service.activeConversation()
    suspend fun createConversation() = service.createConversation(ConversationRequest())
    suspend fun conversation(id: String) = service.conversation(id)
    suspend fun chronicle() = service.chronicle()

    fun streamRuntimeEvents(emit: (RuntimeStoreEvent) -> Unit) {
        val response = service.runtimeEvents().execute()
        if (!response.isSuccessful) {
            response.errorBody()?.close()
            throw RuntimeException("Core Runtime returned HTTP ${response.code()}.")
        }
        val body = response.body() ?: throw RuntimeException("Core Runtime event stream was empty.")
        // `use` guarantees the OkHttp ResponseBody (and its socket) is released on
        // normal exit, cancellation, or error — otherwise every 3s reconnect leaks a connection.
        body.use {
            val source = it.source()
            val parser = RuntimeOperationsSseParser()
            while (!source.exhausted()) {
                parser.consume(source.readUtf8Line() ?: "")?.let(emit)
                if (Thread.currentThread().isInterrupted) return
            }
        }
        throw RuntimeException("Core Runtime event stream ended.")
    }

    fun streamMessage(id: String, content: String, emit: (StreamEvent) -> Unit) {
        val response = service.streamMessage(id, MessageRequest(content, java.util.UUID.randomUUID().toString())).execute()
        if (!response.isSuccessful) {
            response.errorBody()?.close()
            throw RuntimeException("Core Runtime returned HTTP ${response.code()}.")
        }
        val body = response.body() ?: throw RuntimeException("Core Runtime stream was empty.")
        body.use {
            val source = it.source()
            val parser = SseParser()
            while (!source.exhausted()) {
                parser.consume(source.readUtf8Line() ?: "")?.let { event ->
                    emit(event)
                    if (event == StreamEvent.End) return
                }
                // Honor coroutine cancellation so a cancelled conversation stream stops
                // reading instead of holding the socket until the server times out.
                if (Thread.currentThread().isInterrupted) return
            }
        }
    }

    companion object {
        fun create(server: String, token: String): RuntimeApi {
            val base = validateServer(server)
            val clientID = java.util.UUID.randomUUID().toString()
            val auth = Interceptor { chain ->
                val request = chain.request().newBuilder()
                    .header("Authorization", "Bearer $token")
                    .header("X-Bridge-Client-ID", clientID)
                    .build()
                chain.proceed(request)
            }
            val client = OkHttpClient.Builder().addInterceptor(auth).build()
            val retrofit = Retrofit.Builder()
                .baseUrl(base)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            return RuntimeApi(retrofit.create(RuntimeService::class.java))
        }

        fun validateServer(server: String): String {
            val normalized = server.trim().trimEnd('/') + "/"
            val uri = runCatching { URI(normalized) }.getOrNull()
                ?: throw IllegalArgumentException("Enter a valid Core Runtime address.")
            val scheme = uri.scheme?.lowercase()
            require(uri.host != null && (scheme == "https" || (scheme == "http" && isLocal(uri.host)))) {
                "HTTPS is required except for local-network development."
            }
            return normalized
        }

        private fun isLocal(host: String): Boolean {
            val value = host.lowercase()
            return value == "localhost" || value == "127.0.0.1" || value == "::1" ||
                value.endsWith(".local") || value.startsWith("10.") || value.startsWith("192.168.") ||
                value.startsWith("172.")
        }
    }
}

class SseParser(private val gson: Gson = Gson()) {
    private val data = mutableListOf<String>()

    fun consume(line: String): StreamEvent? {
        if (line.isEmpty()) {
            if (data.isEmpty()) return null
            val payload = runCatching {
                gson.fromJson(data.joinToString("\n"), Map::class.java)
            }.getOrNull()
            data.clear()
            val type = payload?.get("type") as? String ?: return null
            return when (type) {
                "phase" -> StreamEvent.Phase(payload["name"] as? String ?: "runtime")
                "delta" -> StreamEvent.Delta(payload["text"] as? String ?: "")
                "end" -> StreamEvent.End
                "error" -> StreamEvent.Error(payload["error"] as? String ?: "Runtime stream error")
                else -> StreamEvent.Metadata
            }
        }
        if (line.startsWith("data:")) data += line.removePrefix("data:").trimStart()
        return null
    }
}
class RuntimeOperationsSseParser(private val gson: Gson = Gson()) {
    private val data = mutableListOf<String>()

    fun consume(line: String): RuntimeStoreEvent? {
        if (line.isEmpty()) {
            if (data.isEmpty()) return null
            val envelope = runCatching { JsonParser.parseString(data.joinToString("\n")).asJsonObject }.getOrNull()
            data.clear()
            val type = envelope?.get("type")?.asString ?: return null
            val payload = envelope.getAsJsonObject("payload") ?: return null
            return when (type) {
                "status" -> RuntimeStoreEvent.Status(gson.fromJson(payload, RuntimeStatus::class.java))
                "diagnostics" -> RuntimeStoreEvent.DiagnosticsChanged(gson.fromJson(payload, Diagnostics::class.java))
                "telemetry" -> RuntimeStoreEvent.Telemetry(gson.fromJson(payload, RuntimeTelemetry::class.java))
                "session" -> RuntimeStoreEvent.Session(gson.fromJson(payload, RuntimeSessionSignal::class.java).currentSession)
                "chronicle" -> RuntimeStoreEvent.Chronicle(gson.fromJson(payload, RuntimeChronicleSignal::class.java).entries)
                "streaming" -> RuntimeStoreEvent.RuntimeStreaming(gson.fromJson(payload, RuntimeStreamingSignal::class.java))
                else -> null
            }
        }
        if (line.startsWith("data:")) data += line.removePrefix("data:").trimStart()
        return null
    }
}