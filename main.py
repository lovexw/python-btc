import sqlite3
import requests
import time
from datetime import datetime
import feedparser
import re
import threading
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import os
import pytz
import ssl
from html import unescape
import json
from collections import defaultdict
import hashlib

# 创建数据目录
if not os.path.exists('data'):
    os.makedirs('data')

# ==========================================
# 密码设置区域（修改密码请更改下面这行）
# ==========================================
ACCESS_PASSWORD = "xiaowuleyi"  # 默认访问密码，可按需修改
# ==========================================

# 初始化数据库
def init_db():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    # 创建表
    c.execute('''CREATE TABLE IF NOT EXISTS crypto_alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  summary TEXT,
                  link TEXT,
                  published TEXT,
                  btc_amount REAL DEFAULT 0,
                  usdt_amount REAL DEFAULT 0,
                  usdc_amount REAL DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 创建每日统计表
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT UNIQUE,
                  btc_total REAL DEFAULT 0,
                  usdt_total REAL DEFAULT 0,
                  usdc_total REAL DEFAULT 0,
                  transaction_count INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 创建BTC价格表
    c.execute('''CREATE TABLE IF NOT EXISTS btc_prices
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT UNIQUE,
                  price_usd REAL DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 创建点赞表
    c.execute('''CREATE TABLE IF NOT EXISTS likes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ip_hash TEXT UNIQUE,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 创建访问统计表
    c.execute('''CREATE TABLE IF NOT EXISTS visit_stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ip_hash TEXT,
                  visit_time DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# 获取客户端IP并哈希处理
def get_client_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        ip = request.environ['REMOTE_ADDR']
    else:
        ip = request.environ['HTTP_X_FORWARDED_FOR']
    # 哈希IP地址以保护隐私
    return hashlib.sha256(ip.encode()).hexdigest()

# 清理HTML标签
def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return unescape(cleantext)

# 解析文本中的加密货币金额
def extract_crypto_amounts(summary):
    # 先清理HTML标签
    clean_summary = clean_html(summary)
    
    btc_amount = 0
    usdt_amount = 0
    usdc_amount = 0
    
    # 添加调试信息
    # print(f"处理原始摘要: {summary}")
    # print(f"清理后摘要: {clean_summary}")
    
    # 提取BTC金额 (匹配#BTC前的数字)
    btc_matches = re.findall(r'([\d,]+\.?\d*)\s*#BTC', clean_summary, re.IGNORECASE)
    for match in btc_matches:
        # 移除逗号并转换为浮点数
        btc_amount += float(match.replace(',', ''))
    
    # 提取USDT金额 (匹配#USDT前的数字)
    usdt_matches = re.findall(r'([\d,]+\.?\d*)\s*#USDT', clean_summary, re.IGNORECASE)
    for match in usdt_matches:
        # 移除逗号并转换为浮点数
        usdt_amount += float(match.replace(',', ''))
    
    # 提取USDC金额 (匹配#USDC前的数字)
    usdc_matches = re.findall(r'([\d,]+\.?\d*)\s*#USDC', clean_summary, re.IGNORECASE)
    for match in usdc_matches:
        # 移除逗号并转换为浮点数
        usdc_amount += float(match.replace(',', ''))
    
    # 添加调试信息
    # print(f"提取到金额 - BTC: {btc_amount}, USDT: {usdt_amount}, USDC: {usdc_amount}")
    # print(f"匹配项 - BTC: {btc_matches}, USDT: {usdt_matches}, USDC: {usdc_matches}")
    
    return btc_amount, usdt_amount, usdc_amount

# 获取BTC价格
def fetch_btc_price():
    try:
        # 使用CoinGecko免费API获取BTC价格
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()
        return data['bitcoin']['usd']
    except Exception as e:
        print(f"获取BTC价格时出错: {e}")
        return None

# 获取BTC价格并存储到数据库
def fetch_and_store_btc_price():
    try:
        price = fetch_btc_price()
        if price is not None:
            conn = sqlite3.connect('data/crypto_monitor.db')
            c = conn.cursor()
            
            # 获取今天的日期
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 插入或更新BTC价格
            c.execute('''INSERT OR REPLACE INTO btc_prices 
                         (date, price_usd)
                         VALUES (?, ?)''',
                      (today, price))
            
            conn.commit()
            conn.close()
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] BTC价格更新: ${price}")
    except Exception as e:
        print(f"存储BTC价格时出错: {e}")

# 获取RSS数据并存储
def fetch_and_store_rss():
    url = "https://rsshub.app/telegram/channel/misttrack_alert"
    
    try:
        # 解决SSL证书问题
        import urllib.request
        import urllib.error
        
        # 创建不验证SSL的上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 使用urllib打开URL
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, context=ssl_context)
        data = response.read()
        
        # 解析RSS
        feed = feedparser.parse(data)
        
        # print(f"获取到 {len(feed.entries)} 条RSS条目")
        
        conn = sqlite3.connect('data/crypto_monitor.db')
        c = conn.cursor()
        
        new_entries = 0
        
        for entry in feed.entries:
            # 检查是否包含指定关键词
            if '#BTC' in entry.summary or '#USDT' in entry.summary or '#USDC' in entry.summary:
                # print(f"找到匹配条目: {entry.title}")
                # 检查是否已存在
                c.execute("SELECT id FROM crypto_alerts WHERE link=?", (entry.link,))
                existing = c.fetchone()
                # print(f"检查链接是否存在: {entry.link}, 结果: {existing}")
                
                if existing is None:
                    # 提取加密货币金额
                    # print("开始提取金额...")
                    btc_amount, usdt_amount, usdc_amount = extract_crypto_amounts(entry.summary)
                    # print(f"提取完成 - BTC: {btc_amount}, USDT: {usdt_amount}, USDC: {usdc_amount}")
                    
                    # 获取本地时间
                    local_tz = pytz.timezone('Asia/Shanghai')
                    local_time = datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 插入新记录
                    # print(f"准备插入记录 - 标题: {entry.title}, 链接: {entry.link}")
                    c.execute('''INSERT INTO crypto_alerts 
                                 (title, summary, link, published, btc_amount, usdt_amount, usdc_amount, timestamp)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                              (entry.title, entry.summary, entry.link, entry.published,
                               btc_amount, usdt_amount, usdc_amount, local_time))
                    new_entries += 1
                    # print(f"成功插入记录")
                # else:
                    # print(f"记录已存在，跳过")
        
        conn.commit()
        conn.close()
        
        # 更新每日统计
        if new_entries > 0:
            update_daily_stats()
            
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 新增 {new_entries} 条记录")
        
    except Exception as e:
        print(f"获取RSS数据时出错: {e}")
        import traceback
        traceback.print_exc()

# 更新每日统计
def update_daily_stats():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    # 获取今天的日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 计算今天的总金额
    c.execute('''SELECT SUM(btc_amount), SUM(usdt_amount), SUM(usdc_amount), COUNT(*) 
                 FROM crypto_alerts 
                 WHERE DATE(timestamp) = ?''', (today,))
    
    result = c.fetchone()
    btc_total = result[0] if result[0] else 0
    usdt_total = result[1] if result[1] else 0
    usdc_total = result[2] if result[2] else 0
    count = result[3] if result[3] else 0
    
    # print(f"今日统计数据 - BTC: {btc_total}, USDT: {usdt_total}, USDC: {usdc_total}, 交易数: {count}")
    
    # 更新或插入每日统计
    c.execute('''INSERT OR REPLACE INTO daily_stats 
                 (date, btc_total, usdt_total, usdc_total, transaction_count)
                 VALUES (?, ?, ?, ?, ?)''',
              (today, btc_total, usdt_total, usdc_total, count))
    
    conn.commit()
    conn.close()

# 定时任务：每5分钟获取一次数据
def scheduled_fetch():
    while True:
        fetch_and_store_rss()
        # 每5分钟执行一次
        time.sleep(300)

# 定时任务：每小时获取一次BTC价格
def scheduled_btc_price_fetch():
    while True:
        fetch_and_store_btc_price()
        # 每小时执行一次
        time.sleep(3600)

# 初始化Flask应用
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session加密，请在生产环境中更改

# 登录页面路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ACCESS_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='密码错误')
    return render_template('login.html')

# 登出路由
@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

# 检查认证的装饰器
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    # 记录访问
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    ip_hash = get_client_ip()
    
    # 插入访问记录
    c.execute("INSERT INTO visit_stats (ip_hash) VALUES (?)", (ip_hash,))
    conn.commit()
    conn.close()
    
    return render_template('index.html')

# 点赞路由
@app.route('/api/like', methods=['POST'])
@login_required
def like():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    ip_hash = get_client_ip()
    
    # 检查是否在24小时内点过赞
    c.execute("""SELECT timestamp FROM likes 
                 WHERE ip_hash = ? 
                 AND timestamp > datetime('now', '-1 day')""", (ip_hash,))
    
    existing_like = c.fetchone()
    
    if existing_like:
        conn.close()
        return jsonify({'success': False, 'message': '24小时内只能点赞一次'})
    
    # 插入新的点赞记录
    c.execute("INSERT INTO likes (ip_hash) VALUES (?)", (ip_hash,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '点赞成功'})

# 获取点赞数
@app.route('/api/likes')
@login_required
def get_likes():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    # 获取总点赞数
    c.execute("SELECT COUNT(*) FROM likes")
    total_likes = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({'likes': total_likes})

# 获取访问统计
@app.route('/api/visit-stats')
@login_required
def get_visit_stats():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    # 获取总访问数
    c.execute("SELECT COUNT(*) FROM visit_stats")
    total_visits = c.fetchone()[0]
    
    # 获取唯一访客数（基于IP哈希）
    c.execute("SELECT COUNT(DISTINCT ip_hash) FROM visit_stats")
    unique_visitors = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_visits': total_visits,
        'unique_visitors': unique_visitors
    })

@app.route('/api/alerts')
@login_required
def get_alerts():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    c.execute('''SELECT * FROM crypto_alerts 
                 ORDER BY timestamp DESC 
                 LIMIT 50''')
    
    alerts = c.fetchall()
    conn.close()
    
    # 转换为字典列表
    result = []
    for alert in alerts:
        result.append({
            'id': alert[0],
            'title': alert[1],
            'summary': alert[2],
            'link': alert[3],
            'published': alert[4],
            'btc_amount': alert[5],
            'usdt_amount': alert[6],
            'usdc_amount': alert[7],
            'timestamp': alert[8]
        })
    
    return jsonify(result)

@app.route('/api/stats')
@login_required
def get_stats():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    c.execute('''SELECT * FROM daily_stats 
                 ORDER BY date DESC 
                 LIMIT 30''')
    
    stats = c.fetchall()
    conn.close()
    
    # 转换为字典列表
    result = []
    for stat in stats:
        result.append({
            'id': stat[0],
            'date': stat[1],
            'btc_total': stat[2],
            'usdt_total': stat[3],
            'usdc_total': stat[4],
            'transaction_count': stat[5],
            'timestamp': stat[6]
        })
    
    return jsonify(result)

@app.route('/api/btc-prices')
@login_required
def get_btc_prices():
    conn = sqlite3.connect('data/crypto_monitor.db')
    c = conn.cursor()
    
    c.execute('''SELECT * FROM btc_prices 
                 ORDER BY date DESC 
                 LIMIT 30''')
    
    prices = c.fetchall()
    conn.close()
    
    # 转换为字典列表
    result = []
    for price in prices:
        result.append({
            'id': price[0],
            'date': price[1],
            'price_usd': price[2],
            'timestamp': price[3]
        })
    
    return jsonify(result)

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动定时任务线程
    fetch_thread = threading.Thread(target=scheduled_fetch)
    fetch_thread.daemon = True
    fetch_thread.start()
    
    # 启动BTC价格获取线程
    btc_price_thread = threading.Thread(target=scheduled_btc_price_fetch)
    btc_price_thread.daemon = True
    btc_price_thread.start()
    
    # 启动Web服务
    app.run(host='0.0.0.0', port=5000, debug=True)