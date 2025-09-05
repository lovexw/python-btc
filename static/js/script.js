let cryptoChart = null;
let currentFilter = 'all';

// 更新统计数据
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        if (stats.length > 0) {
            const todayStats = stats[0];
            document.getElementById('btc-total').textContent = todayStats.btc_total.toFixed(2);
            document.getElementById('usdt-total').textContent = todayStats.usdt_total.toLocaleString();
            document.getElementById('usdc-total').textContent = todayStats.usdc_total.toLocaleString();
            document.getElementById('transaction-count').textContent = todayStats.transaction_count;
        }
    } catch (error) {
        console.error('获取统计数据失败:', error);
    }
}

// 更新访问统计
async function updateVisitStats() {
    try {
        const response = await fetch('/api/visit-stats');
        const stats = await response.json();
        
        document.getElementById('total-visits').textContent = stats.total_visits;
        document.getElementById('unique-visitors').textContent = stats.unique_visitors;
    } catch (error) {
        console.error('获取访问统计失败:', error);
    }
}

// 更新点赞数
async function updateLikeCount() {
    try {
        const response = await fetch('/api/likes');
        const data = await response.json();
        
        document.getElementById('like-count').textContent = data.likes;
    } catch (error) {
        console.error('获取点赞数失败:', error);
    }
}

// 点赞功能
async function like() {
    const likeButton = document.getElementById('like-button');
    
    // 禁用按钮防止重复点击
    likeButton.disabled = true;
    
    try {
        const response = await fetch('/api/like', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 点赞成功，更新点赞数
            updateLikeCount();
            // 显示成功消息
            likeButton.textContent = '已点赞 (' + (parseInt(document.getElementById('like-count').textContent) + 1) + ')';
            setTimeout(() => {
                likeButton.disabled = true;
                likeButton.textContent = '❤ 已点赞 (' + (parseInt(document.getElementById('like-count').textContent) + 1) + ')';
            }, 100);
        } else {
            // 显示错误消息
            alert(data.message);
            likeButton.disabled = false;
        }
    } catch (error) {
        console.error('点赞失败:', error);
        alert('点赞失败，请稍后重试');
        likeButton.disabled = false;
    }
}

// 筛选警报
function filterAlerts(alerts, filter) {
    if (filter === 'all') {
        return alerts;
    }
    
    return alerts.filter(alert => {
        const title = alert.title.toLowerCase();
        switch (filter) {
            case 'btc':
                return title.includes('#btc');
            case 'usdt':
                return title.includes('#usdt');
            case 'usdc':
                return title.includes('#usdc');
            default:
                return true;
        }
    });
}

// 更新警报列表
async function updateAlerts() {
    try {
        const response = await fetch('/api/alerts');
        const alerts = await response.json();
        
        // 应用筛选器
        const filteredAlerts = filterAlerts(alerts, currentFilter);
        
        const tbody = document.getElementById('alerts-body');
        tbody.innerHTML = '';
        
        filteredAlerts.forEach(alert => {
            const row = document.createElement('tr');
            
            // 格式化时间
            const date = new Date(alert.timestamp);
            const formattedDate = date.toLocaleString('zh-CN');
            
            // 只显示原始标题，不添加任何加密货币金额信息
            let titleContent = alert.title;
            
            row.innerHTML = `
                <td>${formattedDate}</td>
                <td>${titleContent}</td>
            `;
            
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('获取警报数据失败:', error);
    }
}

// 更新图表
async function updateChart() {
    try {
        // 获取资金流动数据
        const statsResponse = await fetch('/api/stats');
        const stats = await statsResponse.json();
        
        // 获取BTC价格数据
        const pricesResponse = await fetch('/api/btc-prices');
        const prices = await pricesResponse.json();
        
        // 准备资金流动图表数据
        const labels = stats.map(stat => stat.date).reverse();
        const btcData = stats.map(stat => stat.btc_total).reverse();
        const usdtData = stats.map(stat => stat.usdt_total).reverse();
        const usdcData = stats.map(stat => stat.usdc_total).reverse();
        
        // 准备BTC价格图表数据（与资金流动日期对齐）
        const priceData = [];
        for (const date of labels) {
            const priceEntry = prices.find(p => p.date === date);
            priceData.push(priceEntry ? priceEntry.price_usd : null);
        }
        
        const ctx = document.getElementById('cryptoChart').getContext('2d');
        
        // 如果图表已存在，先销毁
        if (cryptoChart) {
            cryptoChart.destroy();
        }
        
        // 创建新图表
        cryptoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'BTC数量',
                        data: btcData,
                        borderColor: '#f5576c',
                        backgroundColor: 'rgba(245, 87, 108, 0.1)',
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'USDT数量',
                        data: usdtData,
                        borderColor: '#5ee7df',
                        backgroundColor: 'rgba(94, 231, 223, 0.1)',
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'USDC数量',
                        data: usdcData,
                        borderColor: '#d299c2',
                        backgroundColor: 'rgba(210, 153, 194, 0.1)',
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'BTC价格 (USD)',
                        data: priceData,
                        borderColor: '#f2a900', // 橙色，比特币logo颜色
                        backgroundColor: 'rgba(242, 169, 0, 0.1)',
                        fill: false,
                        tension: 0.1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: '数量'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'BTC价格 (USD)'
                        },
                        min: 30000,
                        max: 500000,
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    } catch (error) {
        console.error('获取图表数据失败:', error);
    }
}

// 设置筛选器
function setFilter(filter) {
    currentFilter = filter;
    
    // 更新按钮状态
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.filter-btn[data-filter="${filter}"]`).classList.add('active');
    
    // 更新警报列表
    updateAlerts();
}

// 登出功能
function logout() {
    if (confirm('确定要退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// 定时更新所有数据
function scheduleUpdates() {
    // 立即执行一次
    updateStats();
    updateAlerts();
    updateChart();
    updateLikeCount();
    updateVisitStats();
    
    // 每30秒更新一次统计数据和警报
    setInterval(() => {
        updateStats();
        updateAlerts();
        updateLikeCount();
        updateVisitStats();
    }, 30000);
    
    // 每5分钟更新一次图表
    setInterval(() => {
        updateChart();
    }, 300000);
}

// 页面加载完成后启动更新
document.addEventListener('DOMContentLoaded', function() {
    // 添加登出按钮
    const header = document.querySelector('header');
    const logoutButton = document.createElement('button');
    logoutButton.textContent = '退出登录';
    logoutButton.onclick = logout;
    logoutButton.style.cssText = `
        position: absolute;
        top: 20px;
        right: 20px;
        padding: 8px 16px;
        background: #e74c3c;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    `;
    header.style.position = 'relative';
    header.appendChild(logoutButton);
    
    // 添加筛选按钮事件监听器
    document.querySelectorAll('.filter-btn').forEach(button => {
        button.addEventListener('click', () => {
            const filter = button.getAttribute('data-filter');
            setFilter(filter);
        });
    });
    
    // 添加点赞事件监听器
    document.getElementById('like-button').addEventListener('click', like);
    
    scheduleUpdates();
});