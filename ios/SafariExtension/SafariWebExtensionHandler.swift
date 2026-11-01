import SafariServices

// The extension is plain web code (dist/chrome, built by tools/build_chrome.py); nothing talks to the app.
final class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {
    func beginRequest(with context: NSExtensionContext) {
        context.completeRequest(returningItems: [], completionHandler: nil)
    }
}
