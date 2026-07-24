import XCTest
@testable import BridgeZeroMobile

final class MobileVersionTests: XCTestCase {
    func testCompatibleVersion() {
        XCTAssertTrue(MobileVersion.isCompatible(.init(
            runtimeVersion: "0.2.0", requiredMobileVersion: "0.2.0", apiVersion: "1"
        )))
    }

    func testNewerRequiredVersionIsBlocked() {
        XCTAssertFalse(MobileVersion.isCompatible(.init(
            runtimeVersion: "0.3.0", requiredMobileVersion: "0.3.0", apiVersion: "1"
        )))
    }

    func testDifferentAPIMajorIsBlocked() {
        XCTAssertFalse(MobileVersion.isCompatible(.init(
            runtimeVersion: "0.3.0", requiredMobileVersion: "0.2.0", apiVersion: "2.0"
        )))
    }
}
