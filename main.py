import cv2
import numpy as np
import random
import math
import csv

cap = cv2.VideoCapture('vid_2.avi')

#Yeşil alanı maskeleme
def yesil_maske(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    alt_yesil = np.array([35, 100, 50])
    ust_yesil = np.array([85, 255, 255])
    maske = cv2.inRange(hsv, alt_yesil, ust_yesil)
    return maske


def kirmizi_toplari_bul(frame, yesil_maske):
    kirmizi_toplar = []
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    alt_kirmizi1 = np.array([0, 100, 100])
    ust_kirmizi1 = np.array([10, 255, 255])
    maske1 = cv2.inRange(hsv, alt_kirmizi1, ust_kirmizi1)
    alt_kirmizi2 = np.array([160, 100, 100])
    ust_kirmizi2 = np.array([180, 255, 255])
    maske2 = cv2.inRange(hsv, alt_kirmizi2, ust_kirmizi2)
    maske = cv2.bitwise_or(maske1, maske2)
    maske = cv2.bitwise_and(maske, yesil_maske)
    kernel = np.ones((5, 5), np.uint8)
    maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, kernel)
    maske = cv2.morphologyEx(maske, cv2.MORPH_CLOSE, kernel)
    konturlar, _ = cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for kontur in konturlar:
        (x, y), yaricap = cv2.minEnclosingCircle(kontur)
        if 5 < yaricap < 20:
            kirmizi_toplar.append((int(x), int(y)))

    return kirmizi_toplar

#İki nokta arasındaki mesafeyi hesaplama // öklid
def mesafe(nokta1, nokta2):
    return math.sqrt((nokta1[0] - nokta2[0]) ** 2 + (nokta1[1] - nokta2[1]) ** 2)

top_izleri = {}
top_renkleri = {}
carpisma_sayilari = {}
son_gorulme = {}
top_hizlari = {}
son_carpisma_zamani = {}




#Hareketlerin kaydedileceği CSV dosyasını oluşturma
output_file = 'top_hareketleri.csv'
with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Kare', 'Top_ID', 'X', 'Y', 'Hız_X', 'Hız_Y', 'Çarpışma_Sayısı'])

ret, ilk_kare = cap.read()
if not ret:
    print("Video okunamadı")
    cap.release()
    exit()

yesil_maske = yesil_maske(ilk_kare)

ilk_kirmizi_toplar = kirmizi_toplari_bul(ilk_kare, yesil_maske)
for i, (x, y) in enumerate(ilk_kirmizi_toplar):
    top_izleri[i] = [(x, y)]
    top_renkleri[i] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    carpisma_sayilari[i] = 0
    son_gorulme[i] = 0
    top_hizlari[i] = (0, 0)
    son_carpisma_zamani[i] = -10

#Her karede kırmızı topları işaretleme
kare_sayisi = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    kirmizi_toplar = kirmizi_toplari_bul(frame, yesil_maske)
    kare_sayisi += 1

    
    yeni_top_izleri = {}
    yeni_son_gorulme = {}
    yeni_top_hizlari = {}
    atanan_idler = set()

    for (x, y) in kirmizi_toplar:
        min_mesafe = float('inf')
        min_id = None
        for top_id, iz in top_izleri.items():
            if top_id in atanan_idler:
                continue
            dist = mesafe(iz[-1], (x, y))
            if dist < min_mesafe and dist < 50:  # Eşik değeri: 50 piksel
                min_mesafe = dist
                min_id = top_id
        if min_id is not None:
            yeni_top_izleri[min_id] = top_izleri[min_id] + [(x, y)]
            yeni_son_gorulme[min_id] = kare_sayisi
            atanan_idler.add(min_id)
            # Hız hesaplama
            if len(top_izleri[min_id]) > 1:
                dx = x - top_izleri[min_id][-2][0]
                dy = y - top_izleri[min_id][-2][1]
                yeni_top_hizlari[min_id] = (dx, dy)
            else:
                yeni_top_hizlari[min_id] = top_hizlari[min_id]
        else:
            yeni_id = len(top_izleri) + len(yeni_top_izleri)
            yeni_top_izleri[yeni_id] = [(x, y)]
            top_renkleri[yeni_id] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            carpisma_sayilari[yeni_id] = 0
            yeni_son_gorulme[yeni_id] = kare_sayisi
            yeni_top_hizlari[yeni_id] = (0, 0)
            son_carpisma_zamani[yeni_id] = -10
    
    #Kaybolan topları yeniden tespit etme
    for top_id, iz in top_izleri.items():
        if top_id not in atanan_idler and son_gorulme[top_id] == kare_sayisi - 1:
            yeni_top_izleri[top_id] = top_izleri[top_id]
            yeni_son_gorulme[top_id] = kare_sayisi
            yeni_top_hizlari[top_id] = top_hizlari[top_id]

    top_izleri = yeni_top_izleri
    son_gorulme = yeni_son_gorulme
    top_hizlari = yeni_top_hizlari

    #Çarpışmaları kontrol etme ve çarpışma sayısını arttırma
    idler = list(top_izleri.keys())
    for i in range(len(idler)):
        for j in range(i + 1, len(idler)):
            id1, id2 = idler[i], idler[j]
            if mesafe(top_izleri[id1][-1], top_izleri[id2][-1]) < 22:  #Çarpışma eşiği: 20 piksel
                if son_gorulme[id1] == kare_sayisi and son_gorulme[id2] == kare_sayisi:
                    #Çarpışma durumunda hız ve yön değişikliklerini kontrol etme
                    if top_hizlari[id1] != (0, 0) and top_hizlari[id2] != (0, 0):  # İki top da hareket ediyorsa
                        hiz_farki1 = mesafe(top_hizlari[id1], (0, 0))
                        hiz_farki2 = mesafe(top_hizlari[id2], (0, 0))
                        if hiz_farki1 > 2 or hiz_farki2 > 2:  #Hız değişim eşiği
                            if kare_sayisi - son_carpisma_zamani[id1] > 5 and kare_sayisi - son_carpisma_zamani[id2] > 5:  #Çarpışma sonrası bekleme süresi
                                carpisma_sayilari[id1] += 1
                                carpisma_sayilari[id2] += 1
                                son_carpisma_zamani[id1] = kare_sayisi
                                son_carpisma_zamani[id2] = kare_sayisi

    #Kırmızı topları işaretleme ve izleri çizme
    for i, iz in top_izleri.items():
        renk = top_renkleri[i]
        for j in range(1, len(iz)):
            cv2.line(frame, iz[j-1], iz[j], renk, 2)
        if iz:
            cv2.circle(frame, iz[-1], 10, renk, 2)
            cv2.putText(frame, str(carpisma_sayilari[i]), (iz[-1][0] + 15, iz[-1][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, renk, 2)

            #Hareketi dosyaya yazma
            with open(output_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([kare_sayisi, i, iz[-1][0], iz[-1][1], top_hizlari[i][0], top_hizlari[i][1], carpisma_sayilari[i]])
    
    cv2.imshow('Frame', frame)
    if cv2.waitKey(30) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()


print("Çarpışma Sayıları:")
for top_id, sayi in carpisma_sayilari.items():
    print(f"Top {top_id}: {sayi} çarpışma")
