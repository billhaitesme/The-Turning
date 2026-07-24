import XCTest

final class BridgeZeroMobileUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLoginPresentsOperatorConsoleIdentity() {
        let app = XCUIApplication()
        app.launchArguments += ["-ui-testing"]
        app.launch()

        XCTAssertTrue(app.staticTexts["BRIDGE ZERO"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.textFields["Server Address"].exists)
        XCTAssertTrue(app.secureTextFields["Authentication Token"].exists)
        XCTAssertTrue(app.buttons["CONNECT"].exists)
    }
}
