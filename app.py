import streamlit as st
import requests as req
from bs4 import BeautifulSoup as bs
from datetime import datetime
from pymongo import MongoClient
import pandas as pd
from collections import Counter
import plotly.express as px
import dateparser
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Header User-Agent
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
}

# Koneksi MongoDB
client = MongoClient('mongodb+srv://bolaaa:bolaaa@bolaaaa.mqbmlkh.mongodb.net/?retryWrites=true&w=majority&appName=bolaaaa')
db = client['artikelbola']
collection = db['bolaaaa']

# Fungsi Scraper
def scrape_detik(jumlah_halaman):
    a = 1
    scraped_articles = []
    for page in range(1, jumlah_halaman + 1):
        url = f'https://www.detik.com/search/searchall?query=latihan+sepak+bola&page={page}'
        res = req.get(url, headers=headers)
        soup = bs(res.text, 'html.parser')
        articles = soup.find_all('article', class_='list-content__item')

        if not articles:
            st.warning(f"Halaman {page} tidak ditemukan atau kosong.")
            continue

        for article in articles:
            try:
                a_tag = article.find('h3', class_='media__title').find('a')
                if not a_tag or 'href' not in a_tag.attrs:
                    continue
                link = a_tag['href']
                title = a_tag.get_text(strip=True)

                date_div = article.find('div', class_='media__date')
                date_tag = date_div.find('span') if date_div else None
                date = date_tag['title'] if date_tag else 'Tanggal tidak ditemukan'

                parsed_date = dateparser.parse(date)
                if not parsed_date:
                    st.warning(f"Format tanggal tidak valid: {date}")
                    continue

                detail_page = req.get(link, headers=headers)
                detail_soup = bs(detail_page.text, 'html.parser')
                body = detail_soup.find_all('div', class_='detail__body-text itp_bodycontent')

                if not body:
                    continue

                content = ''
                for section in body:
                    paragraphs = section.find_all('p')
                    content += ''.join(p.get_text(strip=True) for p in paragraphs)

                content = content.replace('ADVERTISEMENT', '').replace('SCROLL TO RESUME CONTENT', '').replace('\n', '')

                article_data = {
                    'title': title,
                    'date': parsed_date.strftime("%Y-%m-%d %H:%M:%S"),
                    'link': link,
                    'content': content
                }

                collection.insert_one(article_data)
                scraped_articles.append(article_data)

                st.success(f'done[{a}] > {title[:40]}...')
                a += 1

            except Exception as e:
                st.error(f"[Error] {e}")
    return scraped_articles

# Streamlit UI
st.title("Scraper Detik: Latihan Sepak Bola")
st.markdown("Masukkan jumlah halaman yang ingin discarping dari Detik.com")

jumlah_halaman = st.number_input("Jumlah Halaman", min_value=1, max_value=20, value=3, step=1)

if st.button("Mulai Scraping"):
    with st.spinner("Sedang mengambil data..."):
        results = scrape_detik(jumlah_halaman)
    st.success(f"Berhasil mengambil {len(results)} artikel.")

    # Tampilkan hasil scraping
    for art in results:
        html_content = f"""
        <div style='border:1px solid #ccc; padding:15px; margin-bottom:10px; border-radius:8px;'>
            <h4>{art['title']}</h4>
            <p><strong>Tanggal:</strong> {art['date']}</p>
            <p><a href="{art['link']}" target="_blank">Baca Artikel</a></p>
            <p>{art['content'][:500]}...</p>
        </div>
        """
        st.markdown(html_content, unsafe_allow_html=True)

    # Grafik Jumlah Artikel per Tahun
    tahun_list = []
    for art in results:
        try:
            parsed_date = datetime.strptime(art['date'], "%Y-%m-%d %H:%M:%S")
            tahun_list.append(parsed_date.year)
        except:
            continue

    counter_tahun = Counter(tahun_list)
    df_tahun = pd.DataFrame({
        'Tahun': list(counter_tahun.keys()),
        'Jumlah Artikel': list(counter_tahun.values())
    }).sort_values('Tahun')

    if df_tahun.empty:
        st.warning("Tidak ada data tahun yang valid untuk ditampilkan dalam grafik.")
    else:
        st.subheader("Grafik Jumlah Artikel per Tahun (Plotly)")
        fig = px.bar(df_tahun, x='Tahun', y='Jumlah Artikel',
                     labels={'Jumlah Artikel': 'Jumlah Artikel', 'Tahun': 'Tahun'},
                     title='Distribusi Artikel per Tahun',
                     color='Jumlah Artikel',
                     text='Jumlah Artikel')
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis=dict(dtick=1))
        st.plotly_chart(fig, use_container_width=True)

        # Pie Chart
        st.subheader("Distribusi Artikel per Tahun (Pie Chart)")
        fig_pie = px.pie(df_tahun, names='Tahun', values='Jumlah Artikel',
                         title='Persentase Artikel per Tahun', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Grafik Jumlah Kata
    st.subheader("Grafik Jumlah Kata dalam Artikel")
    df_kata = pd.DataFrame([{
        'Judul': art['title'],
        'Jumlah Kata': len(art['content'].split())
    } for art in results]).sort_values(by='Jumlah Kata', ascending=False)

    fig_kata = px.bar(df_kata, x='Judul', y='Jumlah Kata',
                      title='Jumlah Kata per Artikel',
                      text='Jumlah Kata',
                      color='Jumlah Kata')
    fig_kata.update_layout(xaxis_tickangle=-45, xaxis_title='Judul Artikel', yaxis_title='Jumlah Kata')
    fig_kata.update_traces(textposition='outside')
    st.plotly_chart(fig_kata, use_container_width=True)

    # Word Cloud
    st.subheader("Word Cloud dari Isi Artikel")
    all_text = ' '.join([art['content'] for art in results])
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_text)
    fig_wc, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig_wc)
