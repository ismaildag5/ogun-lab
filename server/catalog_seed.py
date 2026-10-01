"""100 fictional dishes, ten fictional branches. No third-party data."""
GROUPS = [
 ('Deneme Çorba Evi','Çorba',[
  ('Mercimek çorbası',65),('Ezogelin çorbası',70),('Domates çorbası',75),('Yayla çorbası',70),('Tarhana çorbası',70),
  ('Tavuk suyu çorba',90),('Mantar çorbası',85),('Sebze çorbası',75),('Brokoli çorbası',80),('Düğün çorbası',100)]),
 ('Deneme Dürüm Noktası','Dürüm',[
  ('Tavuk dürüm',180),('Et dürüm',240),('Falafel dürüm',130),('Nohut dürüm',95),('Köfte dürüm',170),
  ('Tantuni dürüm',190),('Çiğ köfte dürüm',85),('Sebzeli dürüm',110),('Kaşarlı tavuk dürüm',195),('Patates dürüm',100)]),
 ('Deneme Pide Fırını','Pide',[
  ('Kıymalı pide',175),('Kaşarlı pide',160),('Kuşbaşılı pide',220),('Ispanaklı pide',140),('Patatesli pide',120),
  ('Karışık pide',230),('Mantarlı pide',165),('Sucuklu pide',195),('Peynirli pide',155),('Lahmacun',90)]),
 ('Deneme Burger Mutfağı','Burger',[
  ('Tavuk burger',150),('Klasik burger',200),('Peynirli burger',220),('Sebzeli burger',155),('Çift köfteli burger',280),
  ('Mantarlı burger',235),('Acılı tavuk burger',160),('Balık burger',195),('Nohut burger',145),('Mini burger',115)]),
 ('Deneme Ev Mutfağı','Ev yemeği',[
  ('Kuru fasulye',110),('Nohut yemeği',105),('Tavuk sote',180),('Et sote',250),('İzmir köfte',195),
  ('Ispanak yemeği',110),('Türlü',120),('Karnıyarık',165),('Bezelye yemeği',115),('Taze fasulye',120)]),
 ('Deneme Pilav Durağı','Pilav',[
  ('Tavuklu pilav',140),('Nohutlu pilav',100),('Sade pirinç pilavı',70),('Bulgur pilavı',65),('Etli pilav',200),
  ('Sebzeli pilav',90),('Mantarlı pilav',100),('Mercimekli bulgur',85),('İç pilav',120),('Fasulye pilav tabağı',165)]),
 ('Deneme Makarna Evi','Makarna',[
  ('Domates soslu makarna',110),('Pesto makarna',150),('Kremalı tavuklu makarna',185),('Bolonez makarna',195),('Peynirli makarna',140),
  ('Mantarlı makarna',155),('Acılı makarna',120),('Sebzeli makarna',125),('Fırın makarna',150),('Yoğurtlu erişte',130)]),
 ('Deneme Salata Bahçesi','Salata',[
  ('Mevsim salata',90),('Çoban salata',95),('Tavuklu salata',175),('Ton balıklı salata',190),('Nohutlu salata',120),
  ('Mercimek salatası',115),('Akdeniz salata',140),('Patates salatası',100),('Bulgur salatası',105),('Izgara sebze tabağı',155)]),
 ('Deneme Kahvaltı Sofrası','Kahvaltı',[
  ('Kaşarlı tost',100),('Karışık tost',135),('Menemen',130),('Sade omlet',100),('Peynirli omlet',125),
  ('Patatesli gözleme',115),('Peynirli gözleme',125),('Ispanaklı gözleme',120),('Simit peynir tabağı',85),('Kahvaltı sandviçi',110)]),
 ('Deneme Tatlı Köşesi','Tatlı',[
  ('Sütlaç',85),('Kazandibi',90),('Tavukgöğsü tatlısı',90),('İrmik helvası',75),('Aşure',95),
  ('Profiterol',120),('Supangle',100),('Mozaik pasta',95),('Fırın sütlaç',100),('Meyve tabağı',110)])
]

def rows():
    for branch_no,(branch,category,meals) in enumerate(GROUPS,1):
        for meal_no,(name,price) in enumerate(meals,1):
            yield {'id':f'm{branch_no:02}{meal_no:02}', 'branch':branch, 'category':category,
                   'name':name, 'portion':'1 porsiyon', 'price_minor':price*100}
