import XCTest
@testable import BridgeZeroMobile

/// IX-D: the iOS console decodes the runtime's command registry and command log exactly as the
/// backend emits them (snake_case; the same shape the Android console consumes).
final class CommandModelsTests: XCTestCase {
    private var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }

    func testDecodesRegistryWithOneCommandPerGate() throws {
        let json = """
        {"commands":[
          {"name":"new_conversation","title":"New conversation","description":"d","risk":"low","gate":"direct","surfaces":["mobile"]},
          {"name":"run_backend_health_check","title":"Run backend health check","description":"d","risk":"medium","gate":"approval","tool_name":"backend_health_check","surfaces":["mobile"]},
          {"name":"change_conversational_routing","title":"Change conversational routing","description":"d","risk":"forbidden","gate":"forbidden","surfaces":[]}
        ],"execution_enabled":true}
        """.data(using: .utf8)!
        let list = try decoder.decode(CommandList.self, from: json)
        XCTAssertEqual(list.commands.map(\.gate), ["direct", "approval", "forbidden"])
        XCTAssertEqual(list.executionEnabled, true)
        XCTAssertEqual(list.commands[1].id, "run_backend_health_check")
    }

    func testDecodesInitiateResponseAwaitingApproval() throws {
        let json = """
        {"command":{"command_id":"cmd-1","name":"run_backend_health_check","risk":"medium","gate":"approval",
                    "requested_by":"operator","channel":"mobile","session_id":"command-console",
                    "requested_at":"2026-08-17T22:31:43+00:00","request_id":"toolreq-1","approval_id":"approval-1",
                    "status":"awaiting_approval","outcome":{"note":"n"},"finished_at":null},
         "pending":[{"request_id":"toolreq-1","approval_id":"approval-1","tool_name":"backend_health_check",
                     "requested_by":"operator:mobile","created_at":"x","expires_at":"y","status":"pending"}]}
        """.data(using: .utf8)!
        let response = try decoder.decode(CommandInitiateResponse.self, from: json)
        XCTAssertEqual(response.command.status, "awaiting_approval")
        XCTAssertEqual(response.command.requestId, "toolreq-1")
        XCTAssertEqual(response.pending?.first?.requestId, "toolreq-1")
    }

    func testDecodesHistoryAndToleratesNullFields() throws {
        let json = """
        {"history":[{"command_id":"cmd-2","name":"new_conversation","risk":"low","gate":"direct","channel":"mobile",
                     "requested_at":"2026-08-17T22:31:46+00:00","request_id":null,"status":"executed","finished_at":"2026-08-17T22:31:46+00:00"}]}
        """.data(using: .utf8)!
        let history = try decoder.decode(CommandHistory.self, from: json)
        XCTAssertEqual(history.history.count, 1)
        XCTAssertNil(history.history[0].requestId)
        XCTAssertEqual(history.history[0].status, "executed")
    }
}
