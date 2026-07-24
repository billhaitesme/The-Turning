import XCTest
@testable import BridgeZeroMobile

final class SSEParserTests: XCTestCase {
    func testDeltaEvent() {
        var parser = SSEParser()
        XCTAssertNil(parser.consume(line: "data: {\"type\":\"delta\",\"text\":\"Core\"}"))
        XCTAssertEqual(parser.consume(line: ""), StreamEvent(kind: .delta("Core")))
    }

    func testRuntimePhaseIsPreserved() {
        var parser = SSEParser()
        _ = parser.consume(line: "data: {\"type\":\"phase\",\"name\":\"guide\"}")
        XCTAssertEqual(parser.consume(line: ""), StreamEvent(kind: .phase("guide")))
    }

    func testUnknownMetadataDoesNotBecomeActivity() {
        var parser = SSEParser()
        _ = parser.consume(line: "data: {\"type\":\"confidence\",\"data\":{}}")
        XCTAssertEqual(parser.consume(line: ""), StreamEvent(kind: .metadata))
    }
}
