import SwiftUI

@main
struct MealieHealthApp: App {
    @State private var bridge = Bridge()
    var body: some Scene {
        WindowGroup { BridgeView(bridge: bridge) }
    }
}

struct BridgeView: View {
    @Bindable var bridge: Bridge
    @State private var deletion = false
    var body: some View {
        NavigationStack {
            Form {
                Section("Your Mealie account") {
                    TextField("https://mealie.example.com", text: $bridge.server).textInputAutocapitalization(.never).autocorrectionDisabled().keyboardType(.URL)
                    SecureField("Personal Mealie API token", text: $bridge.token)
                    Button("Connect and choose Health permissions") { Task { await bridge.connect() } }.disabled(bridge.busy)
                }
                Section("Health synchronisation") {
                    Text("Weight, height, optional body fat, steps, workouts and energy estimates. Only approved data is read. No data is written to Apple Health.")
                    Button("Sync now") { Task { await bridge.sync() } }
                    Text(bridge.status).font(.footnote).accessibilityIdentifier("sync-status")
                    Text("Background updates are best effort. Open this app before your monthly review. Set age, activity assumptions and targets in Mealie.").font(.footnote)
                }
                Section {
                    Button("Disconnect") { Task { await bridge.disconnect(deleteRemote: false) } }
                    Button("Delete synced data and disconnect", role: .destructive) { deletion = true }
                }
            }
            .disabled(bridge.busy || bridge.syncing)
            .navigationTitle("Mealie Health")
            .task { await bridge.resume() }
            .confirmationDialog("Delete your synced measurements and derived goal history from this Mealie server?", isPresented: $deletion, titleVisibility: .visible) {
                Button("Delete and disconnect", role: .destructive) { Task { await bridge.disconnect(deleteRemote: true) } }
            }
        }
    }
}
