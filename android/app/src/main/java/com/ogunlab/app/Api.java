package com.ogunlab.app;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;

final class Api {
 static SharedPreferences prefs(Context c){return c.getSharedPreferences("ogun",Context.MODE_PRIVATE);}
 static String base(Context c){return prefs(c).getString("base","");}
 static String validateBase(String value) throws Exception {
  URI u=new URI(value.trim()); String host=u.getHost();
  if(!"http".equals(u.getScheme()) || host==null || u.getUserInfo()!=null || u.getQuery()!=null || u.getFragment()!=null || (u.getPath()!=null&&!u.getPath().isEmpty()&&!u.getPath().equals("/")))throw new Exception("http://192.168.1.20:8767 gibi bir yerel adres gir.");
  String[] parts=host.split("\\."); if(parts.length!=4)throw new Exception("Yerel IPv4 adresi kullan.");
  int[] n=new int[4];for(int i=0;i<4;i++){n[i]=Integer.parseInt(parts[i]);if(n[i]<0||n[i]>255)throw new Exception("Geçersiz adres.");}
  if(!(n[0]==10||n[0]==127||n[0]==192&&n[1]==168||n[0]==172&&n[1]>=16&&n[1]<=31))throw new Exception("Bu deneme yalnızca yerel ağ içindir.");
  return "http://"+host+":"+(u.getPort()<0?8767:u.getPort());
 }
 static JSONObject call(Context c,String path,JSONObject body) throws Exception {
  return request(base(c),path,body,prefs(c).getString("token",""));
 }
 static JSONObject request(String base,String path,JSONObject body,String token) throws Exception {
  HttpURLConnection conn=(HttpURLConnection)new URL(base+path).openConnection();
  conn.setConnectTimeout(7000);conn.setReadTimeout(10000);conn.setInstanceFollowRedirects(false);
  conn.setRequestProperty("Accept","application/json");
  if(!token.isEmpty())conn.setRequestProperty("Authorization","Bearer "+token);
  try {
   if(body!=null){conn.setRequestMethod("POST");conn.setDoOutput(true);conn.setRequestProperty("Content-Type","application/json");try(var out=conn.getOutputStream()){out.write(body.toString().getBytes(StandardCharsets.UTF_8));}}
   int code=conn.getResponseCode();InputStream stream=code<400?conn.getInputStream():conn.getErrorStream();
   if(stream==null)throw new Exception("Sunucuya ulaşılamadı ("+code+").");
   String text;try(stream){ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int size;while((size=stream.read(buffer))!=-1)bytes.write(buffer,0,size);text=bytes.toString("UTF-8");}
   JSONObject json=new JSONObject(text);if(code>=300)throw new Exception(json.optString("error","Sunucu hatası: "+code));return json;
  } finally {conn.disconnect();}
 }
}
