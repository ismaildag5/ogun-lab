package com.ogunlab.app;
import android.app.Application;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.messaging.FirebaseMessaging;
import org.json.JSONObject;

public class OgunApplication extends Application {
 @Override public void onCreate(){super.onCreate();
  NotificationChannel channel=new NotificationChannel("price_drops","Yemek fiyat düşüşleri",NotificationManager.IMPORTANCE_DEFAULT);
  channel.setDescription("Takip ettiğin deneme yemeklerindeki fiyat değişiklikleri");
  getSystemService(NotificationManager.class).createNotificationChannel(channel);
  initializeFirebase();
 }
 synchronized boolean initializeFirebase(){
  try {
   if(!FirebaseApp.getApps(this).isEmpty())return true;
   String raw=Api.prefs(this).getString("firebase","");if(raw.isEmpty())return false;
   JSONObject c=new JSONObject(raw);
   FirebaseApp.initializeApp(this,new FirebaseOptions.Builder().setApplicationId(c.getString("application_id"))
    .setApiKey(c.getString("api_key")).setGcmSenderId(c.getString("sender_id")).setProjectId(c.getString("project_id")).build());
   FirebaseMessaging.getInstance().setAutoInitEnabled(true);return true;
  }catch(Exception ignored){return false;}
 }
}
