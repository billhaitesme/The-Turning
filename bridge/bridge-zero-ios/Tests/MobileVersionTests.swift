import XCTest
@testable import BridgeZeroMobile

final class MobileVersionTests: XCTestCase {
    func testCompatibleVersion() {
        XCTAssertTrue(MobileVersion.isCompatible(.init(
            runtimeVersion: "0.2.0", requiredMobileVersion: "0.2.0", apiVersion: "1"
        )))
    }

    func testNewerRequiredVersionIsBlocked() {
        // Must stay strictly newer than MobileVersion.current, whatever that is bumped to.
        XCTAssertFalse(MobileVersion.isCompatible(.init(
            runtimeVersion: "99.0.0", requiredMobileVersion: "99.0.0", apiVersion: "1"
        )))
    }

    func testCurrentVersionSatisfiesItself() {
        XCTAssertTrue(MobileVersion.isCompatible(.init(
            runtimeVersion: MobileVersion.current, requiredMobileVersion: MobileVersion.current, apiVersion: "1"
        )))
    }

    func testDifferentAPIMajorIsBlocked() {
        XCTAssertFalse(MobileVersion.isCompatible(.init(
            runtimeVersion: "0.3.0", requiredMobileVersion: "0.2.0", apiVersion: "2.0"
        )))
    }
}
