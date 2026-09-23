package io.github.cyoren.speedready;

import android.content.Context;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.speech.tts.Voice;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;
import java.util.Set;

/**
 * The WebView has no Web Speech API, so the reader gets the platform engine instead.
 * The page wraps this in a stand-in for speechSynthesis, which is why the method names
 * are deliberately close to it.
 */
public class AndroidTTS {

    private final WebView web;
    private final TextToSpeech tts;
    private boolean ready = false;

    AndroidTTS(Context context, WebView web) {
        this.web = web;
        this.tts = new TextToSpeech(context, status -> {
            ready = status == TextToSpeech.SUCCESS;
            if (ready) post("window.dispatchEvent(new Event('voiceschanged'))");
        });
        this.tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override public void onStart(String id) { }
            @Override public void onDone(String id) { post("window.__ttsDone&&__ttsDone(true)"); }
            @Override public void onError(String id) { post("window.__ttsDone&&__ttsDone(false)"); }
            @Override public void onError(String id, int code) { onError(id); }
            @Override public void onStop(String id, boolean started) { }
        });
    }

    private void post(String js) {
        web.post(() -> web.evaluateJavascript(js, null));
    }

    /** [{name, lang}] for every installed voice, in the shape the page expects. */
    @JavascriptInterface
    public String voices() {
        JSONArray out = new JSONArray();
        if (!ready) return out.toString();
        try {
            Set<Voice> all = tts.getVoices();
            if (all == null) return out.toString();
            for (Voice v : all) {
                if (v.getFeatures() != null
                        && v.getFeatures().contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED)) continue;
                JSONObject o = new JSONObject();
                o.put("name", v.getName());
                o.put("lang", v.getLocale().toLanguageTag());
                o.put("quality", v.getQuality());
                out.put(o);
            }
        } catch (Exception ignored) { }
        return out.toString();
    }

    @JavascriptInterface
    public boolean speak(String text, double rate, String voiceName) {
        if (!ready || text == null || text.trim().isEmpty()) return false;
        try {
            if (voiceName != null && !voiceName.isEmpty()) {
                for (Voice v : tts.getVoices()) {
                    if (voiceName.equals(v.getName())) { tts.setVoice(v); break; }
                }
            }
            tts.setSpeechRate((float) rate);
            Bundle params = new Bundle();
            return tts.speak(text, TextToSpeech.QUEUE_FLUSH, params, "speedready")
                    == TextToSpeech.SUCCESS;
        } catch (Exception e) {
            return false;
        }
    }

    @JavascriptInterface
    public void stop() { if (ready) tts.stop(); }

    void shutdown() { tts.stop(); tts.shutdown(); }
}
