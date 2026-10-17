import SwiftUI

@main
struct MovoApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .onOpenURL { model.handlePairing($0) }
                .preferredColorScheme(model.theme == "dark" ? .dark : model.theme == "light" ? .light : nil)
                .tint(Brand.accent)
        }
    }
}

enum Brand {
    static let accent = Color("AccentColor")
}

struct ContentView: View {
    @EnvironmentObject var model: AppModel
    @State private var tab = 0

    var body: some View {
        TabView(selection: $tab) {
            HomeView().tabItem { Label("nav.home", systemImage: "house") }.tag(0)
            ViewerView().tabItem { Label("nav.viewer", systemImage: "doc.richtext") }.tag(1)
            RemoteView().tabItem { Label("nav.remote", systemImage: "dot.radiowaves.left.and.right") }.tag(2)
            SettingsView().tabItem { Label("nav.settings", systemImage: "gearshape") }.tag(3)
        }
        .onChange(of: model.pairedBanner) { paired in if paired { tab = 2 } }
    }
}
