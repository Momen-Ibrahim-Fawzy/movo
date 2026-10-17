import PDFKit
import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

/// In-app viewer for PDFs, slides exported as PDF, and photos — controlled with gestures
/// (iOS does not allow apps to control other apps).
struct ViewerView: View {
    @EnvironmentObject var model: AppModel
    @State private var document: PDFDocument?
    @State private var images: [UIImage] = []
    @State private var page = 0
    @State private var zoom: CGFloat = 1
    @State private var importing = false
    @State private var photoItems: [PhotosPickerItem] = []

    var body: some View {
        NavigationStack {
            Group {
                if let document {
                    PDFViewer(document: document, page: $page, zoom: $zoom)
                } else if !images.isEmpty {
                    TabView(selection: $page) {
                        ForEach(images.indices, id: \.self) { i in
                            Image(uiImage: images[i]).resizable().scaledToFit().scaleEffect(zoom).tag(i)
                        }
                    }
                    .tabViewStyle(.page)
                } else {
                    VStack(spacing: 14) {
                        Image(systemName: "hand.wave").font(.system(size: 54)).foregroundStyle(Brand.gradient)
                        Text("viewer.empty").multilineTextAlignment(.center).foregroundStyle(.secondary)
                    }
                    .padding(32)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .navigationTitle("nav.viewer")
            .toolbar {
                ToolbarItemGroup(placement: .navigationBarTrailing) {
                    Button { importing = true } label: { Image(systemName: "doc.badge.plus") }
                        .accessibilityLabel(Text("viewer.open_pdf"))
                    PhotosPicker(selection: $photoItems, maxSelectionCount: 50, matching: .images) {
                        Image(systemName: "photo.on.rectangle")
                    }
                    .accessibilityLabel(Text("viewer.open_photos"))
                }
            }
            .fileImporter(isPresented: $importing, allowedContentTypes: [.pdf]) { result in
                guard case .success(let url) = result else { return }
                let scoped = url.startAccessingSecurityScopedResource()
                defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                document = PDFDocument(url: url)
                images = []
                page = 0
                zoom = 1
            }
            .onChange(of: photoItems) { items in
                Task {
                    var loaded: [UIImage] = []
                    for item in items {
                        if let data = try? await item.loadTransferable(type: Data.self), let img = UIImage(data: data) { loaded.append(img) }
                    }
                    images = loaded
                    document = nil
                    page = 0
                    zoom = 1
                }
            }
            .onReceive(model.$viewerCommand) { command in
                guard let command else { return }
                apply(command.0)
            }
        }
    }

    private func apply(_ action: ViewerAction) {
        let count = document?.pageCount ?? images.count
        withAnimation(.easeInOut(duration: 0.25)) {
            switch action {
            case .next, .scrollDown: page = min(page + 1, max(count - 1, 0))
            case .previous, .scrollUp: page = max(page - 1, 0)
            case .zoomIn: zoom = min(zoom * 1.2, 5)
            case .zoomOut: zoom = max(zoom / 1.2, 1)
            default: break
            }
        }
    }
}

struct PDFViewer: UIViewRepresentable {
    let document: PDFDocument
    @Binding var page: Int
    @Binding var zoom: CGFloat

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.autoScales = true
        view.displayMode = .singlePage
        view.displayDirection = .horizontal
        view.usePageViewController(true, withViewOptions: nil)
        view.document = document
        return view
    }

    func updateUIView(_ view: PDFView, context: Context) {
        if view.document !== document { view.document = document }
        if let target = document.page(at: page), view.currentPage != target { view.go(to: target) }
        view.scaleFactor = view.scaleFactorForSizeToFit * zoom
    }
}
