import XCTest
@testable import BridgeZeroMobile

final class APIConfigurationTests: XCTestCase {
    func testExternalCleartextServerIsRejectedBeforeNetworkAccess() {
        XCTAssertThrowsError(try APIConfiguration(server: "http://example.com", token: "secret")) { error in
            guard case APIClientError.insecureServer = error else {
                return XCTFail("Expected fail-closed network policy")
            }
        }
    }

    func testHttpsServerBuildsVersionedEndpoint() throws {
        let configuration = try APIConfiguration(server: "https://runtime.example", token: "secret")
        XCTAssertEqual(
            configuration.endpoint("api/mobile/v1/status").absoluteString,
            "https://runtime.example/api/mobile/v1/status"
        )
    }

    func testOfflineStateRetainsRuntimeReason() {
        let state = ConsoleConnection.offline("Core Runtime is unavailable.")
        XCTAssertEqual(state, .offline("Core Runtime is unavailable."))
    }
}
