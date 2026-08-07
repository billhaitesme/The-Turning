import Foundation
import Security

protocol CredentialStoring {
    func saveToken(_ token: String) throws
    func readToken() -> String?
    func deleteToken() throws
}

struct KeychainCredentialStore: CredentialStoring {
    private let service = "arc.omega.bridgezero.mobile"
    private let account = "runtime-bearer-token"

    func saveToken(_ token: String) throws {
        try deleteToken(allowMissing: true)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            kSecValueData as String: Data(token.utf8),
        ]
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.status(status) }
    }

    func readToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func deleteToken() throws { try deleteToken(allowMissing: false) }

    private func deleteToken(allowMissing: Bool) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || (allowMissing && status == errSecItemNotFound) else {
            throw KeychainError.status(status)
        }
    }
}

enum KeychainError: Error {
    case status(OSStatus)
}
