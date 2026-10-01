package com.ogunlab.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.NotificationManager;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.View;
import android.view.WindowInsets;
import android.widget.*;
import com.google.firebase.messaging.FirebaseMessaging;
import org.json.JSONArray;
import org.json.JSONObject;
import java.math.BigDecimal;
import java.text.DateFormat;
import java.text.NumberFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
 final int ink=Color.rgb(35,61,48),green=Color.rgb(48,92,67),paper=Color.rgb(245,245,238),muted=Color.rgb(99,116,106);
 final ExecutorService io=Executors.newSingleThreadExecutor();final Handler handler=new Handler(Looper.getMainLooper());
 LinearLayout root,cards,tabs;TextView status,count;EditText search,budget;Spinner category;
 JSONArray meals=new JSONArray();String mode="budget",deepMeal=null;boolean offline=false,loading=false,renderingCategory=false;
 final Locale tr=Locale.forLanguageTag("tr-TR");
 final Runnable refreshTick=new Runnable(){public void run(){load(false);handler.postDelayed(this,15000);}};
 int dp(float x){return (int)(x*getResources().getDisplayMetrics().density+.5f);}
 TextView text(String value,int size,boolean bold){TextView v=new TextView(this);v.setText(value);v.setTextSize(size);v.setTextColor(ink);v.setPadding(0,dp(5),0,dp(5));if(bold)v.setTypeface(null,Typeface.BOLD);return v;}
 LinearLayout column(){LinearLayout v=new LinearLayout(this);v.setOrientation(LinearLayout.VERTICAL);return v;}
 GradientDrawable background(int color){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(14));d.setStroke(dp(1),Color.rgb(216,224,213));return d;}
 Button button(String title,Runnable click){Button b=new Button(this);b.setText(title);b.setAllCaps(false);b.setTextColor(green);b.setOnClickListener(v->click.run());return b;}
 String money(long amount){return NumberFormat.getCurrencyInstance(tr).format(amount/100.0);}
 String date(double value){return DateFormat.getDateTimeInstance(DateFormat.SHORT,DateFormat.SHORT,tr).format(new Date((long)(value*1000)));}
 void toast(String value){Toast.makeText(this,value,Toast.LENGTH_LONG).show();}
 @Override public void onCreate(Bundle saved){super.onCreate(saved);deepMeal=getIntent().getStringExtra("meal_id");
  ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);root=column();root.setPadding(dp(18),dp(16),dp(18),dp(24));root.setBackgroundColor(paper);scroll.addView(root);setContentView(scroll);
  if(Build.VERSION.SDK_INT>=30)scroll.setOnApplyWindowInsetsListener((v,insets)->{android.graphics.Insets i=insets.getInsets(WindowInsets.Type.systemBars());root.setPadding(dp(18)+i.left,dp(12)+i.top,dp(18)+i.right,dp(24)+i.bottom);return insets;});
  root.addView(text("öğün  /  DENEME MUTFAĞI",24,true));root.addView(text("Aklındaki yemek.\nBeklediğin fiyat.",30,true));
  TextView banner=text("100 yemek · 10 kurgusal mutfak\nTüm fiyatlar deneme verisidir.",13,false);banner.setPadding(dp(14),dp(12),dp(14),dp(12));banner.setBackground(background(Color.rgb(251,244,223)));root.addView(banner);
  LinearLayout tools=new LinearLayout(this);tools.addView(button("Sunucuya bağlan",this::connectionDialog),new LinearLayout.LayoutParams(0,-2,1));tools.addView(button("Bildirim izni",this::notificationPermission),new LinearLayout.LayoutParams(0,-2,1));root.addView(tools);
  status=text("Sunucu bağlantısı hazırlanıyor…",12,false);root.addView(status);
  search=new EditText(this);search.setSingleLine(true);search.setHint("Yemek veya mutfak ara");root.addView(search);
  category=new Spinner(this);root.addView(category);updateCategories();
  tabs=new LinearLayout(this);for(String[] pair:new String[][]{{"budget","Bütçeme göre"},{"drop","Fiyatı düşenler"},{"watch","Takiplerim"}}){Button b=button(pair[1],()->{mode=pair[0];render();});b.setTextSize(11);b.setTag(pair[0]);tabs.addView(b,new LinearLayout.LayoutParams(0,-2,1));}root.addView(tabs);
  budget=new EditText(this);budget.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);budget.setHint("Bütçem (TL)");budget.setText("250");root.addView(budget);
  count=text("",20,true);root.addView(count);root.addView(button("Listeyi yenile",()->load(true)));cards=column();root.addView(cards);
  TextWatcher watcher=new TextWatcher(){public void beforeTextChanged(CharSequence s,int a,int c,int f){}public void onTextChanged(CharSequence s,int a,int b,int c){render();}public void afterTextChanged(Editable e){}};
  search.addTextChangedListener(watcher);budget.addTextChangedListener(watcher);
  category.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onNothingSelected(AdapterView<?> p){}public void onItemSelected(AdapterView<?> p,View v,int pos,long id){if(!renderingCategory)render();}});
  String cache=Api.prefs(this).getString("catalogue","");try{meals=new JSONObject(cache).getJSONArray("items");offline=true;updateCategories();render();}catch(Exception ignored){}
 }
 @Override protected void onResume(){super.onResume();load(false);setupPush();handler.removeCallbacks(refreshTick);handler.postDelayed(refreshTick,15000);}
 @Override protected void onPause(){super.onPause();handler.removeCallbacks(refreshTick);}
 @Override protected void onDestroy(){super.onDestroy();handler.removeCallbacks(refreshTick);io.shutdown();}
 @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);deepMeal=intent.getStringExtra("meal_id");load(true);}
 void updateCategories(){renderingCategory=true;String previous=category.getSelectedItem()==null?"Tümü":category.getSelectedItem().toString();TreeSet<String> values=new TreeSet<>();for(int i=0;i<meals.length();i++)values.add(meals.optJSONObject(i).optString("category"));ArrayList<String> options=new ArrayList<>();options.add("Tümü");options.addAll(values);ArrayAdapter<String> adapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,options);category.setAdapter(adapter);category.setSelection(Math.max(0,options.indexOf(previous)));renderingCategory=false;}
 void load(boolean explain){
  if(loading)return;if(Api.base(this).isEmpty()){status.setText("Önce bilgisayardaki yönetim ekranından kod alıp sunucuya bağlan.");return;}loading=true;
  io.execute(()->{try{JSONObject result=Api.call(this,"/api/catalogue",null);Api.prefs(this).edit().putString("catalogue",result.toString()).apply();runOnUiThread(()->{meals=result.optJSONArray("items");offline=false;loading=false;status.setText("Bağlı · "+Api.base(this)+"\n"+pushStatus());updateCategories();render();openDeepMeal();});}catch(Exception e){runOnUiThread(()->{loading=false;offline=true;status.setText("Sunucuya ulaşılamadı. Son kayıtlar korunuyor.\n"+e.getMessage());render();if(explain)toast(e.getMessage());});}});
 }
 String pushStatus(){NotificationManager n=getSystemService(NotificationManager.class);if(!n.areNotificationsEnabled())return "Telefon bildirimleri kapalı. Bildirim izni düğmesini kullan.";if(Api.prefs(this).getString("firebase","").isEmpty())return "Firebase kurulumu bekleniyor.";if(Api.prefs(this).getString("fcm_token","").isEmpty())return "Bildirim cihaz kaydı hazırlanıyor.";return "Bildirim cihaz kimliği hazır. Teslimi yönetim ekranından doğrula.";}
 void render(){if(cards==null)return;cards.removeAllViews();budget.setVisibility(mode.equals("budget")?View.VISIBLE:View.GONE);for(int i=0;i<tabs.getChildCount();i++){Button b=(Button)tabs.getChildAt(i);b.setTextColor(mode.equals(b.getTag())?Color.WHITE:green);b.setBackgroundTintList(android.content.res.ColorStateList.valueOf(mode.equals(b.getTag())?green:Color.rgb(231,237,223)));}
  String q=search.getText().toString().toLowerCase(tr),cat=category.getSelectedItem()==null?"Tümü":category.getSelectedItem().toString();long limit=0;try{limit=new BigDecimal(budget.getText().toString().replace(',','.')).multiply(new BigDecimal(100)).longValue();}catch(Exception ignored){}
  ArrayList<JSONObject> shown=new ArrayList<>();for(int i=0;i<meals.length();i++){JSONObject x=meals.optJSONObject(i);JSONObject drop=x.optJSONObject("drop"),watch=x.optJSONObject("watch");boolean hasDrop=!offline&&drop!=null&&drop.optBoolean("active")&&drop.optBoolean("big")&&System.currentTimeMillis()/1000.0-drop.optDouble("started_at")<=259200;
   if(!(x.optString("name")+" "+x.optString("branch")).toLowerCase(tr).contains(q)||!cat.equals("Tümü")&&!cat.equals(x.optString("category")))continue;
   if(mode.equals("budget")&&x.optLong("price_minor")>limit||mode.equals("watch")&&watch==null||mode.equals("drop")&&!hasDrop)continue;shown.add(x);}
  shown.sort(Comparator.comparingLong(x->x.optLong("price_minor")));count.setText(shown.size()+" yemek"+(offline?" · son kayıtlar":""));
  if(shown.isEmpty())cards.addView(text(mode.equals("drop")?"Henüz büyük düşüş yok. Yönetim ekranından bir fiyatı düşürerek deneyebilirsin.":"Bu filtrelerde yemek yok.",14,false));
  for(JSONObject x:shown){LinearLayout card=column();card.setPadding(dp(16),dp(14),dp(16),dp(14));card.setBackground(background(Color.WHITE));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(0,dp(10),0,dp(8));cards.addView(card,lp);card.addView(text(x.optString("category")+" · "+x.optString("portion"),12,false));card.addView(text(x.optString("name"),21,true));card.addView(text(x.optString("branch"),12,false));JSONObject drop=x.optJSONObject("drop");if(!offline&&drop!=null&&drop.optBoolean("big")&&drop.optBoolean("active"))card.addView(text("%"+drop.optDouble("percent")+" · "+money(drop.optLong("saved_minor"))+" düşüş",13,true));card.addView(text(money(x.optLong("price_minor")),28,true));card.addView(text("Son değişiklik: "+date(x.optDouble("changed_at")),11,false));JSONObject watch=x.optJSONObject("watch");if(watch!=null)card.addView(text(watch.optString("mode").equals("target")?"Hedefin: "+money(watch.optLong("target_minor")):watch.optString("mode").equals("big")?"Takip: büyük düşüş":"Takip: her düşüş",13,true));card.addView(button(watch==null?"Takip et":"Takibi düzenle",()->watchDialog(x)));card.addView(button("Fiyat geçmişi",()->history(x)));}
 }
 void connectionDialog(){LinearLayout form=column();form.setPadding(dp(22),dp(8),dp(22),0);EditText address=new EditText(this);address.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI);address.setSingleLine(true);address.setHint("http://192.168.1.20:8767");address.setText(Api.base(this));EditText code=new EditText(this);code.setHint("Yönetim ekranındaki 8 karakterli kod");code.setSingleLine(true);form.addView(text("Telefon ve bilgisayar aynı Wi-Fi ağında olmalı.",13,false));form.addView(address);form.addView(code);form.addView(text("Bu geliştirme sürümü yerel ağda HTTP kullanır. Kişisel veya gerçek sipariş verisi girme.",12,false));AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Bilgisayarla eşleştir").setView(form).setNegativeButton("Vazgeç",null).setPositiveButton("Bağlan",null).create();dialog.setOnShowListener(v->dialog.getButton(-1).setOnClickListener(w->{String base;try{base=Api.validateBase(address.getText().toString());}catch(Exception e){toast(e.getMessage());return;}dialog.getButton(-1).setEnabled(false);io.execute(()->{try{JSONObject result=Api.request(base,"/api/pair",new JSONObject().put("code",code.getText().toString()).put("name",Build.MANUFACTURER+" "+Build.MODEL),"");JSONObject config=result.optJSONObject("firebase");Api.prefs(this).edit().putString("base",base).putString("token",result.getString("access_token")).putString("device_id",result.getString("device_id")).putString("firebase",config==null?"":config.toString()).remove("catalogue").apply();runOnUiThread(()->{dialog.dismiss();load(true);setupPush();notificationPermission();});}catch(Exception e){runOnUiThread(()->{dialog.getButton(-1).setEnabled(true);toast(e.getMessage());});}});}));dialog.show();}
 void notificationPermission(){if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},7);else if(!getSystemService(NotificationManager.class).areNotificationsEnabled())startActivity(new Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(android.provider.Settings.EXTRA_APP_PACKAGE,getPackageName()));else toast("Bildirim izni açık. "+pushStatus());}
 void setupPush(){if(Api.base(this).isEmpty()||io.isShutdown())return;io.execute(()->{try{JSONObject config=Api.call(this,"/api/firebase",null).optJSONObject("firebase");if(config!=null)Api.prefs(this).edit().putString("firebase",config.toString()).apply();for(String id:new HashSet<>(Api.prefs(this).getStringSet("receipts",Collections.emptySet()))){Api.call(this,"/api/received",new JSONObject().put("notification_id",id));synchronized(PriceMessagingService.class){Set<String> remaining=new HashSet<>(Api.prefs(this).getStringSet("receipts",Collections.emptySet()));remaining.remove(id);Api.prefs(this).edit().putStringSet("receipts",remaining).commit();}}runOnUiThread(()->{if(!((OgunApplication)getApplication()).initializeFirebase())return;FirebaseMessaging.getInstance().getToken().addOnCompleteListener(task->{if(!task.isSuccessful()){status.setText("Bildirim kaydı alınamadı. İnternet ve Google Play hizmetlerini kontrol et.");return;}String token=task.getResult();Api.prefs(this).edit().putString("fcm_token",token).apply();if(!io.isShutdown())io.execute(()->{try{Api.call(this,"/api/token",new JSONObject().put("token",token));runOnUiThread(()->status.setText("Bağlı · "+pushStatus()));}catch(Exception e){runOnUiThread(()->status.setText("Bildirim kimliği sunucuya kaydedilemedi: "+e.getMessage()));}});});});}catch(Exception ignored){}});}
 void watchDialog(JSONObject meal){LinearLayout form=column();form.setPadding(dp(20),0,dp(20),0);Spinner choice=new Spinner(this);String[] labels={"Her fiyat düşüşünde","Hedef fiyatıma ulaşınca","Büyük düşüşte (%25 ve 40 TL)"},modes={"any","target","big"};choice.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));JSONObject watch=meal.optJSONObject("watch");int index=watch==null?0:Arrays.asList(modes).indexOf(watch.optString("mode"));choice.setSelection(Math.max(0,index));EditText target=new EditText(this);target.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);target.setHint("Hedef fiyat (TL)");target.setText(String.valueOf((watch==null?meal.optLong("price_minor"):watch.optLong("target_minor",meal.optLong("price_minor")))/100.0));form.addView(text(meal.optString("branch"),12,false));form.addView(choice);form.addView(target);target.setVisibility(index==1?View.VISIBLE:View.GONE);choice.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onNothingSelected(AdapterView<?> p){}public void onItemSelected(AdapterView<?> p,View v,int pos,long id){target.setVisibility(pos==1?View.VISIBLE:View.GONE);}});AlertDialog.Builder b=new AlertDialog.Builder(this).setTitle(meal.optString("name")).setView(form).setNegativeButton("Vazgeç",null).setPositiveButton("Kaydet",null);if(watch!=null)b.setNeutralButton("Takibi kaldır",null);AlertDialog dialog=b.create();dialog.setOnShowListener(v->{dialog.getButton(-1).setOnClickListener(w->{try{JSONObject body=new JSONObject().put("meal_id",meal.getString("id")).put("mode",modes[choice.getSelectedItemPosition()]);if(choice.getSelectedItemPosition()==1)body.put("target_minor",new BigDecimal(target.getText().toString().replace(',','.')).multiply(new BigDecimal(100)).longValueExact());saveWatch(dialog,body);}catch(Exception e){toast("Geçerli bir fiyat gir. Örnek: 140 veya 140,50");}});if(watch!=null)dialog.getButton(-3).setOnClickListener(w->{try{saveWatch(dialog,new JSONObject().put("meal_id",meal.getString("id")).put("remove",true));}catch(Exception ignored){}});});dialog.show();}
 void saveWatch(AlertDialog dialog,JSONObject body){dialog.getButton(-1).setEnabled(false);io.execute(()->{try{Api.call(this,"/api/watch",body);runOnUiThread(()->{dialog.dismiss();toast("Takip kaydedildi.");load(true);});}catch(Exception e){runOnUiThread(()->{dialog.getButton(-1).setEnabled(true);toast(e.getMessage());});}});}
 void history(JSONObject meal){io.execute(()->{try{JSONArray rows=Api.call(this,"/api/history/"+meal.getString("id"),null).getJSONArray("items");StringBuilder lines=new StringBuilder();for(int i=0;i<rows.length();i++){JSONObject r=rows.getJSONObject(i);lines.append(date(r.getDouble("changed_at"))).append("  ·  ").append(money(r.getLong("price_minor"))).append("\n\n");}runOnUiThread(()->new AlertDialog.Builder(this).setTitle(meal.optString("name")+" · geçmiş").setMessage(lines.toString()).setPositiveButton("Tamam",null).show());}catch(Exception e){runOnUiThread(()->toast(e.getMessage()));}});}
 void openDeepMeal(){if(deepMeal==null)return;for(int i=0;i<meals.length();i++){JSONObject x=meals.optJSONObject(i);if(deepMeal.equals(x.optString("id"))){deepMeal=null;search.setText(x.optString("name"));category.setSelection(0);mode="budget";budget.setText("100000");render();new AlertDialog.Builder(this).setTitle(x.optString("name")).setMessage(x.optString("branch")+"\nGüncel deneme fiyatı: "+money(x.optLong("price_minor"))+"\nBildirimdeki fiyat daha sonra değişmiş olabilir.").setPositiveButton("Tamam",null).show();break;}}}
}
