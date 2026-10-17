import SwiftUI

struct RemoteView: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("remote.body").foregroundStyle(.secondary)
                    Text("remote.steps").font(.footnote)
                }
                if model.pairedBanner {
                    Section { Label("remote.paired", systemImage: "checkmark.seal") }
                }
                Section {
                    TextField("remote.host", text: $model.remoteHost)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    TextField("remote.port", value: $model.remotePort, format: .number.grouping(.never))
                        .keyboardType(.numberPad)
                    SecureField("remote.code", text: $model.remoteCode)
                        .keyboardType(.numberPad)
                }
                Section {
                    Toggle("remote.use", isOn: $model.remoteEnabled)
                        .onChange(of: model.remoteEnabled) { on in
                            if on && model.running { model.connectRemote() } else if !on { model.disconnectRemote() }
                        }
                    HStack {
                        Text("remote.status")
                        Spacer()
                        Text(LocalizedStringKey("remote.\(model.remoteStatus.rawValue)"))
                            .foregroundStyle(model.remoteStatus == .failed ? .red : .secondary)
                    }
                }
            }
            .navigationTitle("remote.title")
        }
    }
}
