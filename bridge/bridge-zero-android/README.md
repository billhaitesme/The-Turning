# Bridge Zero Mobile for Android

Native Jetpack Compose operator console for the OMEGA-ARC Core Runtime.

**Release:** Epoch IX / Version 0.2.0 · **Milestone:** IX-B

Open this directory in Android Studio with JDK 17 and Android SDK 37 installed. The Gradle Wrapper is a release gate: generate it with the project-pinned Gradle version, commit `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, and `gradle-wrapper.properties`, then verify `./gradlew --version`, `./gradlew test`, and `./gradlew assembleDebug` from a clean checkout. Until those files are present, use Android Studio only for local validation and do not mark Android reproducibility complete.

The project uses the stable Compose BOM `2026.06.00`, Kotlin/Compose compiler `2.3.21`, and Material 3. Credentials are held in EncryptedSharedPreferences backed by Android Keystore as required by the Epoch IX brief. That AndroidX API is now deprecated, so access is isolated in `SecureStore` for a future storage migration.

Release builds disable cleartext traffic at the platform layer. Debug builds allow local HTTP for LAN development, while `RuntimeApi` rejects non-local HTTP hosts. Use HTTPS for release, reverse-proxy, and future cloud deployments. The default trust manager remains intact.

The RuntimeStore consumes `/api/mobile/v1/events`; explicit Refresh is the only REST status probe, and the SSE connection retries after interruption. It does not simulate typing or fabricate subsystem activity; when streaming ends it reloads authoritative conversation history.
