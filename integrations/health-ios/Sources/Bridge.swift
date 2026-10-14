import Foundation
import Observation

final class NoRedirect: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

@MainActor @Observable
final class Bridge {
    var server = Credentials.read("server")
    var token = ""
    var status = "Connect your own Mealie account. No data is shared until you allow Health access."
    var busy = false
    private let health = HealthReader()
    var syncing = false
    private var pending = false
    private let session = URLSession(configuration: .ephemeral, delegate: NoRedirect(), delegateQueue: nil)
    private var identity: String { Credentials.read("server") + "|" + Credentials.read("user") }

    func connect() async {
        guard !busy && !syncing else { return }
        busy = true
        defer { busy = false }
        do {
            guard let url = URL(string: server), url.scheme == "https", url.host != nil,
                  url.user == nil, url.password == nil, url.query == nil, url.fragment == nil else {
                throw BridgeError.message("Use an HTTPS Mealie server URL")
            }
            server = server.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            let proposed = token.isEmpty ? Credentials.read("token") : token
            let me = try await call(path: "/api/users/self", method: "GET", credential: proposed)
            guard let userID = me["id"] as? String else { throw BridgeError.message("Could not identify the account") }
            try Credentials.save(server, key: "server")
            try Credentials.save(proposed, key: "token")
            try Credentials.save(userID, key: "user")
            token = ""
            try await health.authorize()
            status = "Connected. Only data you allow can be read; iOS does not disclose denied read permissions."
            await sync()
            await health.observe { [weak self] in await self?.sync() }
        } catch { status = error.localizedDescription }
    }

    func resume() async {
        guard !Credentials.read("token").isEmpty else { return }
        await health.observe { [weak self] in await self?.sync() }
    }

    func sync() async {
        if syncing { pending = true; return }
        syncing = true
        defer { syncing = false }
        repeat {
            pending = false
            do {
                guard !Credentials.read("token").isEmpty else { throw BridgeError.message("Connect your Mealie account first") }
                health.anchorScope = identity
                let observations = try await health.sampleObservations()
                var deletions = health.deletedIDs
                var offset = 0
                repeat {
                    let end = min(offset + 500, observations.count)
                    let chunk = Array(observations[offset..<end])
                    let deletedChunk = Array(deletions.prefix(500))
                    let encoded = try JSONSerialization.jsonObject(with: JSONEncoder().encode(chunk))
                    var saved = false
                    for _ in 0..<3 {
                        let state = try await call(path: "/api/households/planning/me", method: "GET")
                        guard let revision = state["revision"] as? Int else { throw BridgeError.message("Invalid server revision") }
                        do {
                            _ = try await call(path: "/api/households/planning/me/health?revision=\(revision)", method: "POST",
                                body: ["observations": encoded, "deleted_ids": deletedChunk])
                            saved = true; break
                        } catch BridgeError.message(let message) where message == "Conflict" { continue }
                    }
                    guard saved else { throw BridgeError.message("Server changed repeatedly; retry sync") }
                    offset = end
                    deletions.removeFirst(deletedChunk.count)
                } while offset < observations.count || !deletions.isEmpty
                try health.commitAnchors()
                status = "Synced \(observations.count) records at \(Date().formatted(date: .abbreviated, time: .shortened)). Missing values may mean no measurement or no read permission."
            } catch { status = error.localizedDescription }
        } while pending
    }

    func disconnect(deleteRemote: Bool) async {
        guard !busy && !syncing else { return }
        busy = true
        defer { busy = false }
        do {
            if deleteRemote {
                let state = try await call(path: "/api/households/planning/me", method: "GET")
                let revision = state["revision"] as? Int ?? 0
                _ = try await call(path: "/api/households/planning/me/health?revision=\(revision)", method: "DELETE")
            }
            await health.stop()
            try Credentials.save("", key: "anchors:" + identity)
            Credentials.clear()
            server = ""; token = ""
            status = "Disconnected. Health read permissions can be revoked in iOS Settings."
        } catch { status = error.localizedDescription }
    }

    private func call(path: String, method: String, body: [String: Any]? = nil, credential: String? = nil) async throws -> [String: Any] {
        let destination = credential == nil ? Credentials.read("server") : server
        guard let url = URL(string: destination + path), url.scheme == "https" else { throw BridgeError.message("Invalid HTTPS URL") }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("Bearer \(credential ?? Credentials.read("token"))", forHTTPHeaderField: "Authorization")
        if let body { request.httpBody = try JSONSerialization.data(withJSONObject: body); request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw BridgeError.message("No HTTP response") }
        if http.statusCode == 409 { throw BridgeError.message("Conflict") }
        guard (200..<300).contains(http.statusCode) else { throw BridgeError.message("Server returned \(http.statusCode). Check account, server and data.") }
        return try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
    }
}
