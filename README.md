# Grassphobic - PBP A - Kelompok A07
i. Nama-nama Anggota Kelompok:
1. Adam Rayyan Aryasatya (2406496031)
2. Hannan Afif Darmawan (2406350394)
3. Muhammad Naufal Muzaki (2406428794)
4. Neal Guarddin (2406348282)
5. Rafasya Muhammad Subhan (2406409542)

ii. Deskripsi Aplikasi (Cerita & Manfaat Aplikasi)
### Arena Invicta
**Arena Invicta** adalah platform digital komprehensif yang dirancang khusus untuk para penggemar sepak bola sejati. Aplikasi ini menyajikan dua pilar utama: **berita terkini** dengan analisis mendalam (fitur utama) dan **kuis interaktif** yang menantang. Sebagai "Arena yang Tak Terkalahkan", kami bertujuan menjadi sumber informasi tepercaya yang membedah taktik, melaporkan fakta, dan menjauhkan diri dari gosip murahan. Di sisi lain, kami menyediakan panggung bagi para suporter untuk menguji dan membuktikan pengetahuan mereka, mengubah passion pasif menjadi sebuah pencapaian yang membanggakan. Arena Invicta adalah tempat di mana pecinta olahraga tidak hanya membaca, tetapi juga berpartisipasi dan berkompetisi.

Kebermanfaatan Arena Invicta
Kehadiran Arena Invicta memberikan manfaat nyata bagi para penggunanya dalam tiga area utama:
1. Sebagai Sumber Informasi (Menjadi Lebih Cerdas):
    - **Informasi Terpercaya**: Pengguna mendapatkan akses ke berita yang telah dikurasi, fokus pada fakta dan analisis, bukan sensasi
    - **Wawasan Mendalam**: Meningkatkan pemahaman pengguna tentang taktik, statistik, dan sejarah permainan, membuat mereka menjadi fans yang lebih berpengetahuan.
    - **Hemat Waktu**: Tidak perlu lagi membuka banyak portal berita yang simpang siur, cukup satu sumber yang kredibel dan komprehensif.

2. Sebagai Platform Hiburan (Bersenang-senang dengan Passion):
    - **Hiburan Interaktif**: Kuis memberikan cara baru yang menyenangkan untuk berinteraksi dengan hobi mereka, lebih dari sekadar menonton pertandingan.
    - **Ajang Kompetisi Sehat**: Papan peringkat (leaderboard) memicu semangat kompetisi yang positif antar pengguna untuk menjadi yang terbaik.
    - **Validasi Pengetahuan**: Memberikan panggung bagi pengguna untuk membuktikan dan mengukur seberapa dalam pengetahuan mereka tentang sepak bola.

3. Sebagai Ruang Komunitas (Menemukan Sesama Fans Sejati):
    - **Ruang Diskusi Berkualitas**: Fitur komentar dan profil pengguna memungkinkan terjadinya diskusi yang cerdas dan bermakna dengan orang-orang yang memiliki minat dan level pengetahuan yang sama.
    - **Membangun Reputasi**: Pengguna dapat membangun reputasi sebagai fans yang berpengetahuan luas melalui pencapaian kuis dan komentar analitis mereka di profil.

iii. Daftar Modul\
Modul yang akan diimplementasikan pada Arena Invicta yaitu:
1. **Accounts & Profiles (Admin, Creator, Reader)** - Neal Guarddin ✅\
    Fitur ini mengatur autentikasi pengguna dan profil pengguna, termasuk pembuatan akun, login/logout, dan halaman profil. ✅

    **CRUD:**
    - **Create:** Registrasi akun baru. ✅
    - **Read:** Menampilkan halaman profil pengguna (bio, avatar, tim favorit). ✅
    - **Update:** Mengedit profil. ✅
    - **Delete:** Menghapus atau menonaktifkan akun. ✅

2. **News** - Rafasya Muhammad Subhan\
    Fitur ini menyediakan artikel sepak bola dengan publish dan publish.

    **CRUD:**
    - **Create:** Membuat dan mempublikasikan artikel baru.
    - **Read:** Membaca daftar artikel dan detail berita.
    - **Update:** Mengedit isi/artikel.
    - **Delete:** Menghapus atau men-unpublish artikel.

3. **Quiz** - Hannan Afif Darmawan\
    Fitur kuis interaktif tentang sepak bola. Content Staff dapat membuat kuis dan pertanyaan, sementara pengguna dapat mengikuti kuis dan memperoleh skor.

    **CRUD:**
    - **Create:** Membuat kuis dan pertanyaan.
    - **Read:** Menampilkan daftar kuis dan leaderboard.
    - **Update:** Mengubah pertanyaan atau status publish.
    - **Delete:** Menghapus kuis atau pertanyaan.

4. **Discussions (atau Comment)** - Adam Rayyan Aryasatya\
    Fitur Forum atau kolom komentar untuk berdiskusi dan menanggapi konten.

    **CRUD:**
    - **Create:** Membuat thread atau komentar.
    - **Read:** Melihat thread dan balasan.
    - **Update:** Mengedit komentar sendiri.
    - **Delete:** Menghapus komentar sendiri.

5. **Leagues (Informasi tentang klub yang sedang bertanding)** - Muhammad Naufal Muzaki\
    Fitur ini menampilkan data liga, tim, jadwal pertandingan, hasil, dan informasi terkait lainnya.

    **CRUD:**
    - **Create:** Menambahkan liga, tim, atau jadwal pertandingan.
    - **Read:** Menampilkan informasi liga dan pertandingan.
    - **Update:** Memperbarui skor dan klasemen/standing.
    - **Delete:** Menghapus data tim atau pertandingan.

iv. Sumber Initial Dataset Kategori Utama Produk 

- [News - Articles (Kaggle)](https://www.kaggle.com/datasets/hammadjavaid/football-news-articles/data)  
- [League - Matches Dataset (Hugging Face)](https://huggingface.co/datasets/WideMan/football_matches)


v. Role atau peran pengguna beserta deskripsinya (karena bisa saja lebih dari satu jenis pengguna yang mengakses aplikasi)\
Tentu, ini adalah bagian yang sangat penting dalam merancang sebuah aplikasi. Memiliki peran pengguna (user roles) yang jelas akan menentukan keamanan, alur kerja, dan pengalaman pengguna di Arena Invicta.

Berikut adalah struktur peran pengguna yang bisa diterapkan, dari yang paling dasar hingga yang paling tinggi:

---

### **Peran Pengguna (User Roles) di Arena Invicta**

#### 1. **Pengunjung (Visitor)**

* **Deskripsi:**
    Ini adalah pengguna anonim yang mengakses website tanpa login. Mereka adalah konsumen konten pasif. Tujuannya adalah untuk mendapatkan informasi secara cepat.

* **Hak Akses & Kemampuan:**
    * Membaca semua artikel berita yang sudah dipublikasikan di modul `news`.
    * Melihat halaman klasemen dan jadwal pertandingan di modul `leagues`.
    * Melihat halaman profil publik milik pengguna lain.
    * **Tidak bisa** menulis komentar, mengikuti kuis, atau memiliki halaman profil sendiri.

#### 2. **Anggota Arena (Registered User)**

* **Deskripsi:**
    Ini adalah peran standar untuk setiap pengguna yang telah mendaftar dan login. Mereka adalah inti dari komunitas Arena Invicta. Tujuannya adalah untuk berinteraksi dan berpartisipasi aktif.

* **Hak Akses & Kemampuan:**
    * Memiliki semua hak akses seorang **Pengunjung**.
    * **Membuat dan mengelola profil** mereka sendiri di modul `profiles` (mengubah bio, foto profil, tim favorit).
    * **Mengikuti kuis** di modul `quiz` dan mendapatkan skor yang tersimpan di profil mereka.
    * **Menulis, mengedit, dan menghapus komentar** mereka sendiri di modul `discussions`.
    * Mendapatkan pengalaman yang lebih personal (misalnya, notifikasi atau rekomendasi di masa depan).

#### 3. **Content Staff (Writer + Editor, digabung)**

* **Deskripsi:**
    Ini adalah peran untuk tim konten internal kalian. Mereka adalah para "Jurnalis Arena" yang bertugas membuat konten berkualitas dan mempublikasikan artikelnya.

* **Hak Akses & Kemampuan:**
    * Memiliki semua hak akses seorang **Anggota Arena/Registered User**.
    * **Membuat dan mempublikasikan (Create)** artikel News.
    * **Membaca (Read) daftar artikel, detail berita, dan kuis**.
    * **Mengubah (Update)** artikel berita yang mereka tulis sendiri (selama belum dipublikasikan).
    * **Membuat dan mengelola** set pertanyaan untuk kuis.
    * **Menghapus (Delete)** artikel News ataupun set pertanyaan kuis.

#### 4. **Administrator (Superuser)**

* **Deskripsi:**
    Ini adalah peran tertinggi, biasanya dipegang oleh pemilik produk atau pengembang utama. "Dewa Arena" ini memiliki kontrol penuh atas seluruh aspek teknis dan non-teknis website.

* **Hak Akses & Kemampuan:**
    * Akses tanpa batas ke seluruh fitur dan data di website.
    * **Manajemen pengguna:** Dapat membuat, mengubah, dan menghapus akun pengguna mana pun, serta mengubah peran mereka (misalnya, mengangkat seorang Anggota menjadi Penulis).
    * Kontrol penuh atas seluruh Django Admin, termasuk modul-modul yang tidak bisa diakses peran lain.
    * Bertanggung jawab atas pemeliharaan dan kesehatan sistem secara keseluruhan.

vi. Tautan Deployment PWS dan Link Design

- [PWS](https://neal-guarddin-arenainvicta.pbp.cs.ui.ac.id/)
- [Figma](https://www.figma.com/files/team/1554375848835483944/project/461026907/Grassphobic-Team?fuid=1498580805392729561)

