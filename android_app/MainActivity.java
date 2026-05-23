package com.unobraalsalfa.app;

import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;
import com.onesignal.OneSignal;

public class MainActivity extends AppCompatActivity {

    private WebView myWebView;
    private static final String ONESIGNAL_APP_ID = "YOUR_ONESIGNAL_APP_ID"; // استبدله بـ ID الخاص بك

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // إعداد OneSignal للإشعارات
        OneSignal.setLogLevel(OneSignal.LOG_LEVEL.VERBOSE, OneSignal.LOG_LEVEL.NONE);
        OneSignal.initWithContext(this);
        OneSignal.setAppId(ONESIGNAL_APP_ID);

        // إعداد WebView
        myWebView = (WebView) findViewById(R.id.webview);
        WebSettings webSettings = myWebView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true); // مهم جداً لحفظ تسجيل الدخول

        myWebView.setWebViewClient(new WebViewClient());
        
        // رابط موقعك على Vercel
        myWebView.loadUrl("https://unobraalsalfa.vercel.app/");
    }

    @Override
    public void onBackPressed() {
        if (myWebView.canGoBack()) {
            myWebView.goBack(); // للرجوع للخلف داخل الموقع بدلاً من إغلاق التطبيق
        } else {
            super.onBackPressed();
        }
    }
}
