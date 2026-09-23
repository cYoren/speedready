package io.github.cyoren.speedready;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.webkit.ConsoleMessage;
import android.webkit.CookieManager;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.MimeTypeMap;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * The reader is the same HTML, JavaScript and dictionary that the website serves; it is
 * copied into assets at build time and loaded from there. Nothing is fetched over the
 * network, and the app asks for no permissions.
 *
 * The assets are served under a normal https origin rather than file://, because a
 * file:// page cannot fetch() its own data files and gets unreliable local storage - and
 * everything the reader remembers lives in local storage.
 */
public class MainActivity extends Activity {

    /** Not a real host: nothing leaves the device, requests are answered from assets. */
    private static final String ORIGIN = "https://speedready.invalid/";

    private WebView web;
    private AndroidTTS speech;
    private ValueCallback<Uri[]> filePicker;
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

        setContentView(web);
        hideSystemBarsOnFullscreen();

        if (state != null) web.restoreState(state);
        else web.loadUrl(ORIGIN + "index.html");
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

    private void hideSystemBarsOnFullscreen() {
        View decor = getWindow().getDecorView();
        decor.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
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
    public void onBackPressed() {
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
