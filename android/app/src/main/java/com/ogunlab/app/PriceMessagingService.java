package com.ogunlab.app;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;
import org.json.JSONObject;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.Collections;

public class PriceMessagingService extends FirebaseMessagingService {
 @Override public void onNewToken(String token){
  Api.prefs(this).edit().putString("fcm_token",token).apply();
  if(!Api.base(this).isEmpty())new Thread(()->{try{Api.call(this,"/api/token",new JSONObject().put("token",token));}catch(Exception ignored){}}).start();
 }
 @Override public void onMessageReceived(RemoteMessage message){
  Map<String,String> d=message.getData();String id=d.get("notification_id"),meal=d.get("meal_id");
  if(id==null||meal==null||!meal.matches("m[0-9]{4}")||!Api.prefs(this).getString("device_id","").equals(d.get("device_id")))return;
  try{if(Long.parseLong(d.getOrDefault("expires_at","0"))<System.currentTimeMillis()/1000)return;}catch(Exception e){return;}
  NotificationManager manager=getSystemService(NotificationManager.class);
  if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return;
  if(!manager.areNotificationsEnabled()||manager.getNotificationChannel("price_drops").getImportance()==NotificationManager.IMPORTANCE_NONE)return;
  Set<String> seen=new HashSet<>(Api.prefs(this).getStringSet("seen",Collections.emptySet()));
  if(!seen.contains(id)){
   Intent intent=new Intent(this,MainActivity.class).putExtra("meal_id",meal).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
   PendingIntent pending=PendingIntent.getActivity(this,id.hashCode(),intent,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
   Notification n=new Notification.Builder(this,"price_drops").setSmallIcon(R.drawable.ic_meal)
    .setContentTitle(d.getOrDefault("title","Yemek fiyatı düştü")).setContentText(d.getOrDefault("body",""))
    .setStyle(new Notification.BigTextStyle().bigText(d.getOrDefault("body",""))).setContentIntent(pending).setAutoCancel(true).build();
   manager.notify(id,0,n);if(seen.size()>500)seen.clear();seen.add(id);Api.prefs(this).edit().putStringSet("seen",seen).commit();
  }
  synchronized(PriceMessagingService.class){Set<String> receipts=new HashSet<>(Api.prefs(this).getStringSet("receipts",Collections.emptySet()));receipts.add(id);Api.prefs(this).edit().putStringSet("receipts",receipts).commit();}
  // Phone may be outside the LAN; retry receipt upload when the app resumes.
  new Thread(()->{try{Api.call(this,"/api/received",new JSONObject().put("notification_id",id));synchronized(PriceMessagingService.class){Set<String> pending=new HashSet<>(Api.prefs(this).getStringSet("receipts",Collections.emptySet()));pending.remove(id);Api.prefs(this).edit().putStringSet("receipts",pending).commit();}}catch(Exception ignored){}}).start();
 }
}
