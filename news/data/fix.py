import pandas as pd
import numpy as np

# 1. Load data
file_path = 'data_berita.csv'
df = pd.read_csv(file_path)

# 2. Rename kolom yang typo
df = df.rename(columns={'is_features': 'is_featured'})

# 3. Analisis & Perbaikan Data Tertukar
# Kolom 'category' saat ini isinya nama olahraga (football, dll), kita pindahkan ke 'sports'
if 'football' in df['category'].unique() or 'Sports' not in df.columns:
    df['sports'] = df['category']

# 4. Validasi & Normalisasi Kolom 'Sports'
# Pastikan huruf kapital sesuai (Football, Basketball, dll)
valid_sports = ["Football", "Basketball", "Tennis", "Volleyball", "Motogp"]
# Capitalize setiap kata agar cocok (misal: football -> Football)
df['sports'] = df['sports'].str.title()
# Jika ada olahraga yang tidak valid (selain di list), ganti default ke 'Football' atau biarkan
df.loc[~df['sports'].isin(valid_sports), 'sports'] = "Football"

# 5. Isi Kolom 'Category'
# Karena data kategori asli hilang/tidak ada, kita generate random sesuai list yang valid
valid_categories = ["Update", "Analysis", "Exclusive", "Rumor", "Match"]
df['category'] = np.random.choice(valid_categories, size=len(df))

# 6. Validasi Kolom 'is_featured'
# Pastikan isinya string "True" atau "False" (bukan boolean Python)
# Asumsi data lama ada di kolom 'is_featured' (bekas rename is_features), 
# jika isinya boolean python, ubah ke string.
df['is_featured'] = df['is_featured'].astype(str).replace({'True': 'True', 'False': 'False', '1': 'True', '0': 'False'})
# Pastikan hanya True/False
df.loc[~df['is_featured'].isin(["True", "False"]), 'is_featured'] = "False"

# 7. Reorder Kolom (Fix Urutan Input)
# Kita susun agar rapi, dengan urutan Sports, Category, is_featured berdekatan atau sesuai standar
# Urutan: title, content, sports, category, is_featured, news_views, thumbnail
cols = ['title', 'content', 'sports', 'category', 'is_featured', 'news_views', 'thumbnail']
df = df[cols]

# 8. Save
output_path = 'data_berita_fixed.csv'
df.to_csv(output_path, index=False)

print(f"File berhasil diperbaiki dan disimpan sebagai: {output_path}")
print(df[['sports', 'category', 'is_featured']].head())