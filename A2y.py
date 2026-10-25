import asyncio
import csv
from os import name
import re
from datetime import datetime
import random
from playwright.async_api import Error as PlaywrightError, async_playwright
from playwright.async_api import TimeoutError

def hitung_usia_dan_tanggal(tgl_str):
    """Fungsi helper untuk parsing tanggal lahir YYYY-MM-DD."""
    try:
        clean_tgl = str(tgl_str).replace('"', "").strip()
        p = clean_tgl.split("-")
        tahun = int(p[0])
        bulan_angka = int(p[1])
        tanggal = int(p[2])
        birth = datetime(tahun, bulan_angka, tanggal)
        now = datetime.now()

        age = (
            now.year
            - birth.year
            - ((now.month, now.day) < (birth.month, birth.day))
        )
        return age, tahun, bulan_angka - 1, tanggal  # bulan - 1 sesuai JSON
    except Exception as e:
        print(f"Error parsing tanggal: {e}")
        return 0, 2000, 0, 1

def format_jk(jk_str):
    """Fungsi helper untuk standarisasi Jenis Kelamin."""
    g = str(jk_str).lower().strip().replace('"', "")
    if g in ["laki-laki", "l", "pria", "laki laki", "laki - laki"]:
        return "Laki-Laki"
    return "Perempuan"

async def safe_click(page, selector_or_locator, timeout=3000, max_retries=2):
    """
    Fungsi klik global: Otomatis melepaskan animasi tak stabil
    dan melakukan Refresh (F5) jika terjadi TimeoutError.
    """
    for attempt in range(max_retries):
        try:
            # Jika parameter berbentuk string selector
            if isinstance(selector_or_locator, str):
                locator = page.locator(selector_or_locator)
            else:
                locator = selector_or_locator

            # 1. Coba klik instan lewat JS dulu agar mengabaikan kestabilan animasi
            try:
                await locator.evaluate("el => el.click()", timeout=1500)
                return  # Berhasil
            except Exception:
                pass

            # 2. Jika JS gagal, coba klik standar Playwright dengan force=True
            await locator.click(force=True, timeout=timeout)
            return  # Berhasil

        except TimeoutError:
            print(f"[AUTO-REFRESH] Elemen tidak stabil / Timeout pada percobaan {attempt + 1}. Refreshing (F5)...")
            await page.reload()
            await page.wait_for_load_state("domcontentloaded")

    raise Exception(f"Gagal mengklik elemen setelah {max_retries} kali refresh.")

async def main():
    p = await async_playwright().start()

    # Jalankan Chrome Asli dengan Profil milikmu (Bebas Warning Flag)
    context = await p.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\SEVEN\Documents\chrome_profile",
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=False,
        no_viewport=True,
        args=[
            "--no-sandbox",
            "--start-maximized",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",

        ]
    )
    page_0 = context.pages[0] if context.pages else await context.new_page()
    await page_0.goto(
            "https://sehatindonesiaku.kemkes.go.id/", wait_until="domcontentloaded"
        )
        # 2. Buka Tab 1 untuk ePuskesmas
    page_1 = await context.new_page()
    await page_1.goto(
            "https://purwakarta.epuskesmas.id/", wait_until="domcontentloaded"
        )

    await page_0.bring_to_front()
    page = page_0

    await page.get_by_role("button", name="CKG Umum").click()
    await page.locator('#menu_pelayanan').click();
    
    try:
        await page.locator("#sameLocation").nth(1).click(timeout=3000)
        await page.get_by_role("button", name="Simpan").click(timeout=3000)
    except Exception:
        pass
    
    # 1. BACA FILE CSV (datapendaftaran.csv)
    file_csv = "datapendaftaran.csv"  

    try:
        with open(file_csv, mode="r", encoding="utf-8") as f:
            csv_data = list(csv.reader(f))
    except FileNotFoundError:
        print(f"Error: File '{file_csv}' tidak ditemukan. Pastikan lokasi file benar.")
        return

    if len(csv_data) > 1:
        nik_wali = csv_data[1][0]
        nama_wali = csv_data[1][1]
        usia_wali, tahun_lahir_wali, bulan_lahir_wali, tanggal_lahir_wali = (
            hitung_usia_dan_tanggal(csv_data[1][2])
        )
        jk_wali = format_jk(csv_data[1][3])
        print(
            f"Data Wali Loaded: NIK={nik_wali}, Nama={nama_wali}, Usia={usia_wali}, JK={jk_wali}"
        )
    page_0.set_default_timeout(5000)  
   
    # ==========================================
    # 4. LOOPING PEMROSESAN DATA (Mulai Baris Ke-3 / Index 2)
    # ==========================================
    for baris in range(2, len(csv_data)):
        print(f"\n--- Memproses Data Baris Ke-{baris + 1} ---")

        await page.get_by_role("button", name="CKG Umum").click()
        # 2. PARSING DATA DARI CSV
        nik = csv_data[baris][0]
        nama = csv_data[baris][1]
        jk = format_jk(csv_data[baris][3])
        no_wa = csv_data[baris][4]
        usia, tahun_lahir, bulan_lahir, tanggal_lahir = hitung_usia_dan_tanggal(csv_data[baris][2])

        status_menikah = csv_data[baris][5]
        pekerjaan = csv_data[baris][6]
        prov = csv_data[baris][7]
        kab = csv_data[baris][8]
        kec = csv_data[baris][9]
        kel = csv_data[baris][10]
        domisili = csv_data[baris][11]

        print(f"Data NIK aktif: {nik} | Nama: {nama} | | Usia : {usia}| Pekerjaan: {pekerjaan}")
        try:
            usia_val = int(usia)
        except (NameError, ValueError, TypeError):
            usia_val = 0

        jk_clean = str(jk).strip().lower()
        #  3. NAVIGASI AWAL MENU

        await page.get_by_role("button", name="CKG Umum").click()

        await page.locator("[id=\"menu_cari/daftarkan_individu\"]").click()
        try:
            await page.get_by_role("button", name="Daftar Baru").click()
        except Exception:
            pass

        # Form Data Peserta
        await page.get_by_role('textbox', name='NIK *').fill(nik)
        try:
            await page.locator("id=Nama Lengkap").fill(nama)
        except Exception:
            pass
   
        # 1. PILIH TANGGAL LAHIR DATEPICKER
        await page.locator("xpath=//*[@id='Tanggal Lahir']/div[2]/div/div").click()
        await page.locator("xpath=/html/body/div[3]/div/div/div/span/button[2]").click()
        await asyncio.sleep(0.2)

        jumlah_klik = int((2029 - tahun_lahir) / 10) if (1900 <= tahun_lahir <= 2029) else 13
        for _ in range(jumlah_klik):
            await page.locator("css=button.mx-btn-icon-double-left").click()

        await page.locator(f"xpath=//div[text()='{tahun_lahir}']").click()
        await page.locator(f"xpath=//table[contains(@class,'mx-table-month')]//td[@data-month='{bulan_lahir}']").click()
        await page.locator(f"xpath=//table[contains(@class,'mx-table-date')]//td[not(contains(@class, 'not-current-month'))]//div[text()='{tanggal_lahir}']").click()
        await asyncio.sleep(0.2)

        # 2. PILIH JENIS KELAMIN (DROPDOWN)
        await page.get_by_text("Pilih jenis kelamin", exact=True).click()
        if jk.lower() == 'laki-laki':
            await page.get_by_text("Laki-laki", exact=True).last.click()
        else:
            await page.get_by_text("Perempuan", exact=True).last.click()
        
        # 3. ISI NOMOR WHATSAPP
        await page.locator("id=No Whatsapp").fill(no_wa)
        await asyncio.sleep(0.2)

        try:
            if int(usia) >= 60:
                await page.locator("#noWali").nth(1).click()
        except Exception as e:
            print(f"[INFO] Klik #noWali dilewati / tidak ditemukan: {e}")
                
        tanggal_sekarang = str(datetime.now().day)
        try:
            await page.locator(f"xpath=//button[span[text()='{tanggal_sekarang}']]").first.click(force=True)
        except Exception:
            await page.get_by_text(tanggal_sekarang, exact=True).last.click(force=True)
        tombol_simpan = page.locator("form button").filter(has_text="Simpan").first
        if await tombol_simpan.is_visible():
            await tombol_simpan.click(force=True)
        else:
            await page.locator("xpath=//form//button").last.click(force=True)
        await asyncio.sleep(1)

        # 1. PENANGANAN POP-UP KONDISIONAL
        skip_ke_baris_berikutnya = False
        try:
            popup = page.locator("xpath=//div[contains(@class, 'z-1000') or contains(@class, 'backdrop-blur') or contains(@class, 'modal')]").last
            await popup.wait_for(state="visible", timeout=2000)
            teks_popup = (await popup.text_content()).lower()
            print(f"Pop-up terdeteksi: {teks_popup.strip()[:60]}...")
            if "valid" in teks_popup and "tidak" not in teks_popup:
                print(" Status: Data Peserta Valid -> Klik Lanjutkan")
                try:
                    await page.get_by_role("button", name="Lanjutkan").click(force=True, timeout=2000)
                except Exception:
                    pass
                skip_ke_baris_berikutnya = False
            elif "tidak valid" in teks_popup:
                print(" Status: Data peserta tidak valid -> Skip")
                try:
                    await page.get_by_role("button", name="Periksa Kembali").click()
                    await page.get_by_role("button").filter(has_text=re.compile(r"^$")).first.click()
                except Exception:
                    pass
                skip_ke_baris_berikutnya = True
            elif ("sudah menerima layanan" in teks_popup or "terdaftar" in teks_popup):
                print(" Status: Sudah Menerima Layanan -> Skip")
                try:
                    await page.get_by_role("button", name="Cari Individu").click(force=True, timeout=2000)
                except Exception:
                    pass
                skip_ke_baris_berikutnya = True
            elif ("data tidak ditemukan" in teks_popup):
                print(" Status: nik tidak terdapat di database -> Skip")
                try:
                    await page.get_by_role("button", name="Periksa Kembali").click()
                    await page.get_by_role("button").filter(has_text=re.compile(r"^$")).first.click()
                except Exception:
                    pass
                skip_ke_baris_berikutnya = True
            else:
                print(" Status: Pop-up Lain -> Skip")
                skip_ke_baris_berikutnya = True

        except Exception:
            print(" Tidak ada pop-up, lanjut ke Data Pendukung...")
            skip_ke_baris_berikutnya = False

        # JUMP JIKA POP-UP MEMINTA SKIP
        if skip_ke_baris_berikutnya:
            print(" Skipping Data Pendukung -> Lanjut ke CSV berikutnya.\n")
            await asyncio.sleep(1)
            continue
        # 2. ISI DATA PENDUKUNG (DIAMANKAN DENGAN TRY)
        print(" Mulai mengisi Data Pendukung...")
        try:
            try:
                await page.get_by_text("Pilih status pernikahan").click(timeout=5000)
            except Exception:
                await page.locator("xpath=//form/div/div/div[2]/div/div[2]/div").click(force=True, timeout=5000)

            await page.get_by_text(status_menikah, exact=True).click(force=True, timeout=5000)
            # B. Pekerjaan
            try:
                await page.get_by_text("Pilih pekerjaan").click(timeout=5000)
            except Exception:
                await page.get_by_role("textbox", name="Cari pekerjaan").fill(pekerjaan)
            await asyncio.sleep(0.2)

            await page.get_by_text(pekerjaan, exact=True).first.click(force=True)
            # 1. Buka modal / dropdown alamat domisili
            await page.get_by_text("Pilih alamat domisili").click(force=True)
            await asyncio.sleep(0.2)

            # 2. Provinsi
            await page.get_by_role("textbox", name="Cari Provinsi").fill(prov)
            await asyncio.sleep(0.2)
            await page.get_by_text(prov, exact=True).first.click(force=True)  # Klik hasil pencarian
            await asyncio.sleep(0.2)

            # 3. Kabupaten / Kota
            await page.get_by_role("textbox", name="Cari Kabupaten/Kota").fill(kab)
            await asyncio.sleep(0.2)
            await page.get_by_text(kab, exact=True).first.click(force=True)  # Klik hasil pencarian
            await asyncio.sleep(0.2)

            # 4. Kecamatan
            await page.get_by_role("textbox", name="Cari Kecamatan").fill(kec)
            await asyncio.sleep(0.2)
            await page.get_by_text(kec, exact=True).first.click(force=True)  # Klik hasil pencarian
            await asyncio.sleep(0.2)

            # 5. Kelurahan / Desa
            await page.get_by_role("textbox", name="Cari Kelurahan").fill(kel)
            await asyncio.sleep(0.2)
            await page.get_by_text(kel, exact=True).first.click(force=True)  # Klik hasil pencarian
            await asyncio.sleep(0.2)

            await page.get_by_role("textbox", name="Detail Alamat Domisili *").fill(domisili)
            await asyncio.sleep(0.2)

            await page.get_by_role("button", name="Daftarkan").click()
            await asyncio.sleep(0.2)

            popup_sukses = page.locator("xpath=//div[contains(., 'Berhasil Daftar')]").last
            await popup_sukses.wait_for(state="visible", timeout=3000)
            
            await asyncio.sleep(0.2)
            # 2. Ambil elemen yang berisi teks 'No. Tiket:'
            teks_tiket = await page.get_by_text("No. Tiket:").text_content()
            # 3. Ambil kode tiketnya saja (misal: 'W4T-K7H')
            no_tiket = teks_tiket.split(":")[-1].strip()
            print(f"Kode Tiket: {no_tiket}")

            # 4. Klik tombol Tutup
            await page.get_by_role("button", name="Tutup").click(force=True)
            await asyncio.sleep(0.3)
            print(" Berhasil menyimpan Data Pendukung!")
            await asyncio.sleep(0.3)

        except Exception as err_data:
            print(f" Error saat mengisi Data Pendukung: {err_data}")

        await page_0.locator("#menu_pelayanan").click(force=True)
        await asyncio.sleep(0.3)

        # 1. Pilih Filter Dropdown "Nomor Tiket"
        try:
            await page_0.locator("div.border-rd-r-0 span").first.click(force=True, no_wait_after=True)
            await page_0.locator("div").filter(has_text=re.compile(r"^Nomor Tiket$")).first.click(force=True)
        except Exception:
            pass  # Jika dropdown sudah otomatis 'Nomor Tiket'

        # 2. Isi Nomor Tiket pada Tab 0
        input_tiket = page_0.get_by_role("textbox", name="0/")
        await input_tiket.click()
        await input_tiket.fill(no_tiket.strip())
        await asyncio.sleep(0.3)

        # 3. Tekan Enter 2x via Keyboard Playwright Murni (Tanpa pyautogui)
        await page_0.keyboard.press("Enter")
        await asyncio.sleep(0.3)
        await page_0.keyboard.press("Enter")
        await asyncio.sleep(1.2)

        # 4. Eksekusi Tombol Mulai & Simpan Pemeriksaan
        try:
            await page_0.get_by_role("button", name="Mulai").click(
                force=True, timeout=3000
            )
            await page_0.get_by_role("button", name="Mulai Pemeriksaan").click(
                force=True, timeout=3000
            )
            await page_0.get_by_role("button", name="Simpan").click(
                force=True, timeout=3000
            )
        except Exception as e:
            print(f"[INFO] Tombol Mulai/Simpan dilewati: {e}")
        #=============EPUSKESMAS==============#
        await page_1.bring_to_front()
        await page_1.get_by_role("button", name="Pendaftaran").click()
        await page_1.get_by_role("link", name="Pasien & KK").click()
        await page_1.get_by_role("textbox", name="Cari NIK / No Asuransi").fill(nik)
        await page_1.get_by_role("button", name="Cari").click()
        await page_1.get_by_role("cell", name="1", exact=True).dblclick()
        await page_1.get_by_role("cell", name="1", exact=True).dblclick()
        await page_1.get_by_role("cell", name="1", exact=True).dblclick()
        await page_1.locator("#table_data_anamnesa").get_by_role("cell", name="1", exact=True).dblclick()
        sistole = await page_1.locator("#sistole").input_value()
        diastole = await page_1.locator("#diastole").input_value()
        tinggi_badan = await page_1.locator("#tinggi_badan").input_value()
        berat_badan = await page_1.locator("#berat_badan").input_value()
        lingkar_perut = await page_1.locator('input[name="PeriksaFisik[lingkar_perut]"]').input_value()
        locator_riwayat = page_1.locator("xpath=/html/body/section/div/div[2]/div[3]/div[8]/div[2]/div[2]")

        # 2. Cek keberadaan elemen tanpa membuat skrip crash/timeout
        if await locator_riwayat.count() > 0:
            Riw_Penyakit = (await locator_riwayat.inner_text()).strip()
        else:
            Riw_Penyakit = ""

        # 3. Tentukan variabel Hipertensi berdasarkan isi teks Riw_Penyakit
        if "hipertensi" in Riw_Penyakit.lower():
            hipertensi = "Ya"
        else:
            hipertensi = "Tidak"

        if "diabetes mellitus" in Riw_Penyakit.lower():
            diabetes_mellitus = "Ya"
        else:
            diabetes_mellitus = "Tidak"

        print(f"Riwayat Penyakit: '{Riw_Penyakit}'")
        print(f"Status Hipertensi: {hipertensi}")
        print(f"Status diabetes mellitus: {diabetes_mellitus}")
        
        # Menampilkan hasil salinan di terminal
        print(f"Sistole: {sistole}, Diastole: {diastole}, TB: {tinggi_badan}, BB: {berat_badan}, LP: {lingkar_perut},")
        locator_merokok = page_1.locator(
            'input[name="Anamnesa[merokok]"][value="1"]'
        )

        # storeChecked: Menghasilkan True jika tercentang, False jika tidak
        Merokok = await locator_merokok.is_checked()

        # 2. Konversi ke status 'Ya' atau 'Tidak'
        Riw_Merokok = "Ya" if Merokok else "Tidak"

        # 3. Tampilkan hasil di terminal untuk dipastikan
        print(f"Status Checked (Merokok): {Merokok}")
        print(f"Hasil Riw_Merokok      : {Riw_Merokok}")

        await page_1.get_by_role("link", name="Laboratorium").click()
        GDS = page_1.locator("xpath=//*[@id='tabel_detail_riwayat']/tr[1]/td[7]/ul/li[2]")

        # Pastikan eksekusi dilakukan di Tab 0 (ASIKS)
        await page_0.bring_to_front()

        # ==========================================
        # 1. MODUL HIPERTENSI & TEKANAN DARAH
        # ==========================================
        try:
            try:
                await page_0.locator(
                    "xpath=//*[@id='rowfrm000265']/button/div/div"
                ).click(force=True, timeout=3000)
            except Exception:
                pass

            if hipertensi == "Ya":
                await page_0.locator("label").filter(has_text="Ya").locator(
                    "span"
                ).first.click(force=True)
            else:
                await page_0.locator("label").filter(has_text="Tidak").locator(
                    "span"
                ).first.click(force=True)

            val_usia = "60" if int(usia) > 60 else "36"
            try:
                await page_0.locator("#sq_101i").fill(val_usia, timeout=1000)
            except Exception:
                pass

            sistole_val = str(max(50, int(sistole))) if sistole else "50"
            diastole_val = str(max(50, int(diastole))) if diastole else "50"

            await page_0.locator("#sq_102i").fill(sistole_val)
            await page_0.locator("#sq_103i").fill(diastole_val)
            await page_0.get_by_role("button", name="Kirim").click(force=True)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[SKIP 1s] Modul Hipertensi dilewati: {e}")

        # ==========================================
        # 2. MODUL GDS / DIABETES MELLITUS
        # ==========================================
        try:
            try:
              await page_0.locator("#rowfrm000256").get_by_role("button", name="Input Data").click()
            except Exception:
                pass

            if diabetes_mellitus == "Ya":
                await page_0.locator("label").filter(has_text="Ya").locator(
                    "span"
                ).first.click(force=True)
            else:
                await page_0.locator("label").filter(has_text="Tidak").locator(
                    "span"
                ).first.click(force=True)

            try:
                umur = int(usia) if "usia" in locals() and str(usia).isdigit() else 30
                val_bulan = (
                    str(random.randint(5, 10) * 12)
                    if umur > 60
                    else str(random.randint(2, 5) * 12)
                )
                await page_0.get_by_role(
                    "spinbutton", name="Sudah Berapa Bulan Anda"
                ).fill(val_bulan, timeout=500)
            except Exception:
                pass

            await page_0.get_by_role("button", name="Kirim").click(
                force=True, timeout=1000
            )
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[SKIP 1s] Modul GDS dilewati: {e}")
        # ==========================================
        # 3. MODUL GIZI BB, TB, LP
        # ==========================================
        try:
            try:
                await page_0.locator("#rowfrm000051").get_by_role("button", name="Input Data").click()
            except Exception:
                await page_0.locator("#rowfrm000093").get_by_role("button", name="Input Data").click(force=True, timeout=3000)

            tb_val = (
                str(tinggi_badan)
                if "tinggi_badan" in locals() and tinggi_badan
                else "0"
            )
            bb_val = (
                str(berat_badan) if "berat_badan" in locals() and berat_badan else "0"
            )
            lp_val = (
                str(lingkar_perut)
                if "lingkar_perut" in locals() and lingkar_perut
                else "0"
            )

            fields = [
                ("#sq_100i", bb_val, "Berat Badan"),
                ("#sq_101i", tb_val, "Tinggi Badan"),
                ("#sq_102i", lp_val, "Lingkar Perut"),
            ]

            for selector, val, label in fields:
                await page_0.wait_for_selector(selector, timeout=3000)
                await page_0.fill(selector, val)
                await page_0.get_by_role("button", name="Kirim").click(
                    force=True, timeout=3000
                )
                print(f"Berhasil mengisi {label} ({selector}): {val}")
        except Exception as e:
            print(f"[SKIP 1s] Modul Gizi dilewati: {e}")
        # ==========================================
        # PERILAKU MEROKOK & ANAMNESA (DENGAN AWAIT LENGKAP)
        # ==========================================
        try:
            try:
                await page_0.get_by_role("row", name="Hasil Perilaku Merokok Input").get_by_role("button").click()
            except Exception:
                pass   
            if Riw_Merokok == "Ya":
                await page_0.get_by_label("1. Apakah Anda merokok dalam").locator("label").filter(has_text="Ya").locator("span").first.click()
                await page_0.locator("label").filter(has_text="Keduanya").locator("span").first.click()
                await page_0.get_by_label("5. Apakah Anda terpapar asap").locator("label").filter(has_text="Ya").locator("span").first.click()
            else:
                await page_0.get_by_label("1. Apakah Anda merokok dalam").locator("label").filter(has_text="Tidak").locator("span").first.click()
                await page_0.get_by_label("2. Apakah Anda pernah merokok").locator("label").filter(has_text="Tidak").locator("span").first.click()
                await page_0.get_by_label("3. Apakah Anda terpapar asap").locator("label").filter(has_text="Tidak").locator("span").first.click()
            try:
                await page_0.get_by_role("button", name="Kirim").click()
            except Exception:
                pass
        except Exception as e:
            print(f"[SKIP 1s] Modul Perilaku Merokok dilewati: {e}")
        # ==========================================
        # 5. MODUL AKTIVITAS FISIK
        # ==========================================
        try:
            await page_0.get_by_role("row", name="Tingkat Aktivitas Fisik Input").get_by_role("button").click()
            byk_aktivitas = str(random.randint(3, 7))
            lama_aktivitas = str(random.randint(3, 6) * 10)
            await page_0.get_by_label("1. Apakah Anda melakukan").locator("label").filter(has_text="Ya").click()
            await page_0.get_by_role("spinbutton", name="Berapa hari dalam satu minggu").first.fill(byk_aktivitas)
            await page_0.get_by_role("spinbutton", name="Dalam satu hari berapa menit").first.fill(lama_aktivitas)
            await page_0.get_by_label("4. Apakah Anda melakukan").locator("label").filter(has_text="Ya").click()
            await page_0.get_by_label("5. Berapa hari dalam satu").fill(byk_aktivitas)
            await page_0.get_by_label("6. Dalam satu hari berapa").fill(lama_aktivitas)
            await page_0.get_by_label("7. Apakah Anda melakukan").locator("label").filter(has_text="Ya").click()
            await page_0.get_by_label("8. Berapa hari dalam satu").fill(byk_aktivitas)
            await page_0.get_by_label("9. Dalam satu hari berapa").fill(lama_aktivitas)
            await page_0.get_by_label("10. Apakah Anda melakukan").locator("label").filter(has_text="Tidak").click()
            await page_0.get_by_label("11. Apakah Anda melakukan").locator("label").filter(has_text="Tidak").click()
            await page_0.get_by_label("12. Apakah Anda melakukan").locator("label").filter(has_text="Tidak").click()
            await page_0.get_by_role("button", name="Kirim").click()
            await page_0.wait_for_timeout(3000)
        except Exception as e:
            print(f"[SKIP 1s] Modul Aktivitas Fisik dilewati: {e}")
        # ==========================================
        # 6. FAKTOR RISIKO TB - MANDIRI
        # ==========================================
        if usia_val >= 18:
            try:
                await page_0.get_by_role("row", name="Faktor Risiko TB - Mandiri").get_by_role("button").click(force=True)
            except Exception:
                pass
        try:
            await page_0.locator("label").filter(has_text="Tidak batuk").locator("span").first.click()
            await page_0.get_by_role("button", name="Kirim").click()
        except Exception as e:
            print(f"[SKIP 1s] Modul TB Mandiri dilewati: {e}")
        # ==========================================
        # 7. PENAPISAN KANKER PARU
        # ==========================================
        if usia_val >= 45:
            try:
                try:
                    await page_0.get_by_role("row", name="Penapisan Risiko Kanker Paru").get_by_role("button").click()
                except Exception:
                    pass
                await page_0.wait_for_timeout(500)
                questions = [
                    "#sq_100",
                    "#sq_102",
                    "#sq_103",
                    "#sq_104",
                    "#sq_105",
                    "#sq_101",
                ]
                for q_id in questions:
                    radio_option = page_0.locator(
                        f"{q_id} fieldset > div:nth-child(2) label"
                    )
                    await radio_option.click()
                await page_0.locator('#sv-nav-complete input[value="Kirim"]').click(force=True)
            except Exception as e:
                print(f"[SKIP 1s] Modul Kanker Paru dilewati: {e}")
        # ==========================================
        # 8. FAKTOR RISIKO HATI
        # ==========================================
        try:
            try:
                await page_0.get_by_role("row", name="Faktor Risiko Hati Input Data").get_by_role("button").click(force=True)
            except Exception:
                pass

            await page_0.wait_for_timeout(300)

            # Klik semua opsi secara instan lewat DOM browser
            await page_0.evaluate("""() => {
                for (let i = 100; i <= 108; i++) {
                    const el = document.querySelector(`#sq_${i} fieldset > div:nth-child(2) label`);
                    if (el) el.click();
                }
            }""")

            await page_0.get_by_role("button", name="Kirim").click(force=True)

        except Exception as e:
            print(f"[SKIP 1s] Modul Risiko Hati dilewati: {e}")
        # ==========================================
        # 9.Kesehatan Jiwa Dewasa
        # ==========================================
        try:
            # 1. Abaikan error jika tombol "rowfrm000067" / "Gunakan Data" tidak muncul (!errorignore = true)
            try:
                await page_0.get_by_role("row", name="Kesehatan Jiwa Dewasa Input").get_by_role("button").click()
            except (TimeoutError, PlaywrightError):
                print(
                    "Tombol 'Gunakan Data' (rowfrm000067) tidak ditemukan, melanjutkan ke pengisian form..."
                )

            # 2. Klik opsi radio pertama (div:nth-child(1)) pada pertanyaan sq_100 hingga sq_103
            questions = ["#sq_100", "#sq_101", "#sq_102", "#sq_103"]

            for q_id in questions:
                # Menargetkan opsi ke-1 (div:first-child) di tiap pertanyaan SurveyJS
                radio_option = page_0.locator(f"{q_id} fieldset > div:first-child label")
                await radio_option.click()

            # 3. Klik tombol Kirim (sv-nav-complete)
            await page_0.locator('#sv-nav-complete input[value="Kirim"]').click()
            print("Berhasil mengisi form dan mengirimkan data.")

        except Exception as e:
            print(f"Terjadi kesalahan tidak terduga: {e}")    
        # ==========================================
        # Faktor Risiko Kanker Usus
        # ==========================================
        if usia_val >= 45:
            try:
                # 1. Klik tombol utama dengan force=True
                await page_0.get_by_role("row", name="Faktor Risiko Kanker Usus").get_by_role("button").click(force=True)

                # 2. Pertanyaan 1 & sq_101
                await page_0.locator("label:has-text('Tidak') span").first.click(force=True)
                await page_0.locator("#sq_101 fieldset > div:nth-child(2) label").click(force=True)

                # 3. Pertanyaan Merokok
                merokok_text = "Ya" if str(Riw_Merokok).strip().lower() == "ya" else "Tidak"
                await page_0.locator(f"label:has-text('{merokok_text}') span").first.click(force=True)

                # 4. Parse variabel Usia & Jenis Kelamin
                try:
                    usia_val = int(usia)
                except (NameError, ValueError, TypeError):
                    usia_val = 0

                jk_val = str(jk).lower().strip() if "jk" in locals() else ""

                # 5. Skor APCS (Usia)
                if usia_val < 50:
                    usia_text = "<50 tahun"
                elif 50 <= usia_val <= 69:
                    usia_text = "- 69 tahun"
                else:
                    usia_text = ">= 70 tahun"

                await page_0.locator(f"label:has-text('{usia_text}') span").first.click(force=True)

                # 6. Jenis Kelamin
                if "laki" in jk_val:
                    await page_0.locator("label:has-text('Laki-Laki')").first.click(force=True)
                elif any(k in jk_val for k in ["perempuan", "wanita"]):
                    await page_0.locator("label:has-text('Perempuan')").first.click(force=True)

                # 7. Kirim
                await page_0.get_by_role("button", name="Kirim").click(force=True)

            except Exception as e:
                print(f"Modul KANKER USUS dilewati: {e}")
        # ==========================================
        # MODUL KANKER LEHER RAHIM
        # ==========================================
        # 1. Parsing Variabel Jenis Kelamin & Usia
        jk_clean = str(jk).strip().lower()

        try:
            usia_val = int(usia)
        except (NameError, ValueError, TypeError):
            usia_val = 0

        # 2. Ketentuan Logika (Perempuan & Usia 30 s/d 70 tahun)
        if jk_clean == "perempuan" and 30 <= usia_val <= 70:
            try:
                # Klik tombol induk menggunakan ID CSS
                await page_0.locator("#rowfrm000088 button").click(force=True, no_wait_after=True)

                # Cek status menikah
                st_nikah_clean = str(status_menikah).lower().strip()
                pilihan = "Ya" if any(k in st_nikah_clean for k in ["kawin", "menikah", "ya"]) else "Tidak"

                # Klik opsi jawaban
                await page_0.locator(f"label:has-text('{pilihan}') span").first.click(force=True)

                # Klik tombol Kirim
                await page_0.get_by_role("button", name="Kirim").click(force=True)

            except Exception as e:
                print(f"[SKIP] Gagal mengisi Modul Kanker Leher Rahim: {e}")

        # ==========================================
        # 12. DEMOGRAFI DEWASA LAKI-LAKI
        # ==========================================
        if jk_clean == "laki-laki" and 17 <= usia_val <= 59:
            try:
                # 1. Gunakan CSS ID langsung & set timeout singkat jika elemen sudah pasti ada
                await page_0.locator("#rowfrm000006 button").click(force=True)

                st_nikah = str(status_menikah).strip().lower()

                # 2. Tentukan teks label target
                if "belum" in st_nikah:
                    label_text = "Belum Menikah"
                elif "cerai mati" in st_nikah:
                    label_text = "Cerai Mati"
                elif "cerai hidup" in st_nikah:
                    label_text = "Cerai Hidup"
                elif any(k in st_nikah for k in ["menikah", "kawin"]):
                    label_text = "Menikah"
                else:
                    label_text = None

                # 3. Gunakan locator langsung tanpa chaining filter berlebih
                if label_text:
                    await page_0.locator(f"label:has-text('{label_text}') span").first.click(force=True)

                await page_0.locator("label:has-text('Non disabilitas') span").first.click(force=True)
                
                await page_0.get_by_role("button", name="Kirim").click(force=True)

            except Exception as e:
                print(f"[SKIP] Modul Demografi Dewasa Laki dilewati: {e}")
        # ==========================================
        # 13. DEMOGRAFI DEWASA PEREMPUAN
        # ==========================================
        if jk_clean == "perempuan" and 17 <= usia_val <= 59:
            try:
                # 1. Gabungkan ID dan button langsung tanpa XPath
                await page_0.locator("#rowfrm000007 div > div").first.click(force=True, no_wait_after=True)

                # 2. Parsing usia secara efisien
                try:
                    usia_val = int(usia)
                except (NameError, ValueError, TypeError):
                    usia_val = 0

                # 3. Tentukan selector opsi berdasarkan usia
                child_idx = 2 if usia_val >= 25 else 1
                
                # 4. Gunakan force=True pada klik label/radio agar tidak menunggu cek visual DOM
                await page_0.locator(f"#sq_100 fieldset > div:nth-child({child_idx}) label").click(force=True)
                await page_0.locator("#sq_102 fieldset > div:nth-child(2) label").click(force=True)
                await page_0.locator("#sq_103 fieldset > div:nth-child(1) label").click(force=True)

                # 5. Tombol kirim
                await page_0.locator('#sv-nav-complete input[value="Kirim"]').click(force=True)
            except Exception as e:
                print(f"[SKIP] Modul Demografi Dewasa Perempuan dilewati: {e}")
        # ==========================================
        # 13. Riwayat Imunisasi Tetanus(Status T)
        # ==========================================
        # 2. Ketentuan Logika (Perempuan, Usia >= 18 dan < 40)
        if jk_clean == "perempuan" and 18 <= usia_val < 40:
            try:
                await page.get_by_role("row", name="Riwayat Imunisasi Tetanus(").get_by_role("button").click()
                await page.locator("label").filter(has_text="Pernah imunisasi tetanus tetapi tidak ingat berapa kali").locator("span").first.click()
                await page.get_by_role("button", name="Kirim").click()
            except Exception as e:
                    print(f"[SKIP] Riwayat Imunisasi Tetanus(Status T)n dilewati: {e}")
        # ==========================================
        # 15. DEMOGRAFI LANSIA
        # ==========================================
        if usia_val >= 60:
            try:
                try:
                    await page_0.get_by_role("row", name="Demografi Lansia Input Data").get_by_role("button").click(force=True)
                except Exception:
                    pass

                usia_val = int(usia) if "usia" in locals() and str(usia).isdigit() else 0
                if usia_val >= 67:
                    await page_0.locator(
                        "#sq_100 fieldset > div:nth-child(3) label"
                    ).click()
                else:
                    await page_0.locator(
                        "#sq_100 fieldset > div:nth-child(2) label"
                    ).click()

                await page_0.locator("#sq_101 fieldset > div:nth-child(1) label").click()
                await page_0.locator('#sv-nav-complete input[value="Kirim"]').click()
            except Exception as e:
                print(f"[SKIP 1s] Modul Demografi Lansia dilewati: {e}")

        # ==========================================
        #       SELESAIKAN
        # ==========================================
        await page_0.get_by_role("button", name="Selesaikan Layanan").click()
        await page_0.get_by_role("button", name="Konfirmasi").click()
        await page.get_by_role("button", name="CKG Umum").click()
        await page.locator("[id=\"menu_cari/daftarkan_individu\"]").click()

        print(f"--- Selesai Memproses Baris CSV Ke-{baris + 1} ---")
        continue

    # ==========================================
    # SETELAH SEMUA CSV SELESAI DIPROSES
    # ==========================================
    print("\nSeluruh data CSV telah selesai diproses.")
    try:
        await page_0.pause()
    except Exception:
        pass

    try:
        await context.close()
        await p.stop()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n[INFO] Program dihentikan secara manual oleh pengguna.")