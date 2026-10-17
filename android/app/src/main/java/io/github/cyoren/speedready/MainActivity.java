package io.github.cyoren.speedready;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.MimeTypeMap;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.window.OnBackInvokedDispatcher;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * The reader is the same HTML, JavaScript and dictionary that the website serves; it is
 * copied into assets at build time and loaded from there. Nothing is fetched over the
 * network except a language pair's dictionary, downloaded once.
 *
 * The assets are served under a normal https origin rather than file://, because a
 * file:// page cannot fetch() its own data files and gets unreliable local storage - and
 * everything the reader remembers lives in local storage.
 */
public class MainActivity extends Activity {

    /** Not a real host: nothing leaves the device, requests are answered from assets. */
    private static final String ORIGIN = "https://speedready.invalid/";

    private WebView web;
    private FrameLayout root;
    private AndroidTTS speech;
    private ValueCallback<Uri[]> filePicker;
    /** A book handed over by another app ("Open with"), served once at ORIGIN + "shared-file". */
    private volatile Uri shared;
    private static final int PICK_FILE = 1;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);          // the reader is a JavaScript application
        s.setDomStorageEnabled(true);          // progress, learned words and bookmarks
        s.setAllowFileAccess(false);           // assets only; no reading the filesystem
        s.setAllowContentAccess(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setTextZoom(100);                    // the app has its own text size control
        CookieManager.getInstance().setAcceptCookie(false);

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage m) {
                Log.d("SpeedreadyWeb", m.message() + "  (" + m.sourceId() + ":" + m.lineNumber() + ")");
                return true;
            }

            @Override
            public void onPermissionRequest(PermissionRequest r) { r.deny(); }

            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb,
                                             FileChooserParams params) {
                filePicker = cb;
                Intent i = params.createIntent();
                try {
                    startActivityForResult(i, PICK_FILE);
                } catch (Exception e) {
                    filePicker = null;
                    return false;
                }
                return true;
            }
        });

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (u.toString().startsWith(ORIGIN)) return false;    // our own pages
                startActivity(new Intent(Intent.ACTION_VIEW, u));     // dictionary links go to the browser
                return true;
            }

            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest req) {
                String url = req.getUrl().toString();
                if (!url.startsWith(ORIGIN)) return null;             // nothing else is reachable anyway
                String path = url.substring(ORIGIN.length());
                int cut = path.indexOf('?');
                if (cut >= 0) path = path.substring(0, cut);
                if (path.equals("shared-file")) return sharedFile();
                if (path.isEmpty()) path = "index.html";
                try {
                    InputStream in = getAssets().open(path);
                    Map<String, String> headers = new HashMap<>();
                    headers.put("Access-Control-Allow-Origin", ORIGIN);
                    return new WebResourceResponse(mimeOf(path), "utf-8", 200, "OK", headers, in);
                } catch (IOException e) {
                    return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found",
                            new HashMap<>(), null);
                }
            }
        });

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            web.setForceDarkAllowed(false);   // the page themes itself
        }

        speech = new AndroidTTS(this, web);
        web.addJavascriptInterface(speech, "AndroidTTS");   // only our own assets are ever loaded

        web.addJavascriptInterface(this, "AndroidShell");

        // Android 15+ draws apps edge to edge, and older WebViews report no env(safe-area-inset-*), so the
        // header would sit under the status bar and Start under the gesture bar: pad natively instead.
        root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(0x10, 0x10, 0x12));
        root.addView(web);
        root.setOnApplyWindowInsetsListener((v, in) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets i = in.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                v.setPadding(i.left, i.top, i.right, i.bottom);
                return WindowInsets.CONSUMED;
            }
            return in;
        });
        setContentView(root);

        // Android 16 no longer calls onBackPressed() for apps targeting it (predictive back)
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::back);
        }

        takeShared(getIntent());
        if (state != null) web.restoreState(state);
        else web.loadUrl(ORIGIN + "index.html");
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (takeShared(intent)) web.evaluateJavascript("window.openShared&&openShared()", null);
    }

    private boolean takeShared(Intent intent) {
        if (intent == null || !Intent.ACTION_VIEW.equals(intent.getAction()) || intent.getData() == null) return false;
        shared = intent.getData();
        return true;
    }

    private WebResourceResponse sharedFile() {
        Uri u = shared;
        shared = null;
        Map<String, String> headers = new HashMap<>();
        try {
            if (u == null) throw new IOException("nothing shared");
            String name = "book.epub";
            try (Cursor c = getContentResolver().query(u, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) {
                if (c != null && c.moveToFirst() && c.getString(0) != null) name = c.getString(0);
            } catch (Exception ignored) { }
            if ("text/plain".equals(getContentResolver().getType(u)) && !name.toLowerCase().endsWith(".txt")) name += ".txt";
            headers.put("X-Name", Uri.encode(name));
            return new WebResourceResponse("application/octet-stream", null, 200, "OK", headers,
                    getContentResolver().openInputStream(u));
        } catch (Exception e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", headers, null);
        }
    }

    /** The page's light/dark setting: colors the bars' background and their icons to match. */
    @JavascriptInterface
    public void theme(String hex) {
        runOnUiThread(() -> {
            int c;
            try { c = Color.parseColor(hex); } catch (Exception e) { return; }
            if (root != null) root.setBackgroundColor(c);
            boolean light = Color.luminance(c) > 0.5f;
            if (Build.VERSION.SDK_INT >= 30) {
                int flags = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                getWindow().getInsetsController().setSystemBarsAppearance(light ? flags : 0, flags);
            }
            if (Build.VERSION.SDK_INT < 35) {
                getWindow().setStatusBarColor(c);
                getWindow().setNavigationBarColor(c);
            }
        });
    }

    private static String mimeOf(String path) {
        if (path.endsWith(".json") || path.endsWith(".webmanifest")) return "application/json";
        if (path.endsWith(".html")) return "text/html";
        if (path.endsWith(".js")) return "text/javascript";
        if (path.endsWith(".svg")) return "image/svg+xml";
        String ext = MimeTypeMap.getFileExtensionFromUrl(path);
        String guess = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext);
        return guess != null ? guess : "application/octet-stream";
    }

    @Override
    protected void onActivityResult(int req, int result, Intent data) {
        if (req == PICK_FILE && filePicker != null) {
            filePicker.onReceiveValue(FileChooserParamsCompat.parse(result, data));
            filePicker = null;
            return;
        }
        super.onActivityResult(req, result, data);
    }

    /** Turns the picker result into the array the WebView expects. */
    static final class FileChooserParamsCompat {
        static Uri[] parse(int result, Intent data) {
            if (result != RESULT_OK || data == null || data.getData() == null) return null;
            return new Uri[]{data.getData()};
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() { back(); }   // Android 12 and older

    private void back() {
        // let the page close its own sheets first
        web.evaluateJavascript(
                "(function(){var s=document.querySelector('.sheet.on');if(s){s.classList.remove('on');return 'handled'}return 'exit'})()",
                value -> {
                    if (value == null || !value.contains("handled")) finish();
                });
    }

    @Override
    protected void onPause() { super.onPause(); web.onPause(); }

    @Override
    protected void onResume() { super.onResume(); web.onResume(); }

    @Override
    protected void onDestroy() {
        if (speech != null) { speech.shutdown(); speech = null; }
        if (web != null) { web.destroy(); web = null; }
        super.onDestroy();
    }
}
