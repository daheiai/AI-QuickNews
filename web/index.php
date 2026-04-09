<?php
/**
 * AI 快讯 Landing Page
 * 瀑布流展示多期速报，支持无限滚动加载
 */

require_once __DIR__ . '/config.php';

// 获取历史速报列表
$history = get_history_list();
$total_issues = count($history);

// 首次加载 20 期
$initial_count = 20;
$display_items = array_slice($history, 0, $initial_count);

// 统计数据
$latest_data = load_quick_data();
$latest_issue = $latest_data['issue_number'] ?? $total_issues;

// 预加载首批卡片数据
$cards = [];
foreach ($display_items as $item) {
    $data = load_quick_data($item['filename'] . '.json');
    if (!$data) continue;

    // 收集本期品牌
    $brands = [];
    $brand_logos = [];
    foreach ($data['items'] ?? [] as $news_item) {
        if (!empty($news_item['brands'])) {
            foreach ($news_item['brands'] as $brand) {
                if (!in_array($brand, $brands) && count($brands) < 5) {
                    $brands[] = $brand;
                    $logo = get_brand_logo($brand);
                    if ($logo) {
                        $brand_logos[] = ['brand' => $brand, 'logo' => $logo];
                    }
                }
            }
        }
    }

    $cards[] = [
        'filename' => $item['filename'],
        'date' => $item['date'],
        'time' => $item['time'],
        'issue_number' => $data['issue_number'] ?? '?',
        'summary' => str_replace(['【', '】'], ['', ''], $data['summary'] ?? ''),
        'item_count' => count($data['items'] ?? []),
        'brand_logos' => $brand_logos,
    ];
}

$has_more = $total_issues > $initial_count;
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大黑AI速报 - 每4小时更新的AI行业快讯｜AI日报</title>
    <meta name="description" content="大黑AI速报（AI日报/AI快讯）：每4小时自动更新，涵盖模型动态、产品工具、技巧教程、硬件动态、行业资讯，快速了解最新AI热点。">
    <meta name="keywords" content="AI速报,AI日报,AI快讯,AI新闻,每日AI,AI热点,大黑AI速报,大黑AI日报,大模型,OpenAI,Claude,Gemini,Qwen,DeepSeek">
    <meta property="og:title" content="大黑AI速报（AI日报/AI快讯）">
    <meta property="og:description" content="每4小时更新的AI速报与AI日报摘要，瀑布流浏览历史期次，快速掌握最新AI热点。">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://news.daheiai.com/">
    <link rel="stylesheet" href="css/style.css">
    <link rel="alternate" type="application/rss+xml" title="大黑AI速报 RSS" href="rss.php">
    <style>
        /* Landing Page 专用样式 */
        .landing-wrapper {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            min-height: 100vh;
            background: var(--bg-color);
        }

        /* Hero 区域 */
        .hero {
            text-align: center;
            padding: 60px 20px 50px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 40px;
        }

        .hero-avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            margin-bottom: 20px;
            border: 3px solid var(--border-color);
        }

        .hero-title {
            font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
            font-size: 2.2rem;
            font-weight: 900;
            color: var(--text-color);
            margin: 0 0 12px 0;
            letter-spacing: 2px;
        }

        .hero-subtitle {
            font-size: 1.1rem;
            color: var(--sub-text);
            margin: 0 0 30px 0;
            font-weight: 400;
        }

        .hero-stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 30px;
        }

        .hero-stat {
            text-align: center;
        }

        .hero-stat-number {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 2rem;
            font-weight: 900;
            color: var(--text-color);
        }

        .hero-stat-label {
            font-size: 0.85rem;
            color: var(--sub-text);
            margin-top: 4px;
        }

        .hero-buttons {
            display: flex;
            justify-content: center;
            gap: 16px;
            flex-wrap: wrap;
        }

        .hero-btn {
            display: inline-block;
            padding: 12px 28px;
            font-size: 0.95rem;
            text-decoration: none;
            border-radius: 6px;
            transition: all 0.2s;
        }

        .hero-btn-primary {
            background: var(--text-color);
            color: var(--bg-color);
        }

        .hero-btn-primary:hover {
            opacity: 0.85;
        }

        .hero-btn-secondary {
            background: transparent;
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }

        .hero-btn-secondary:hover {
            background: var(--banner-bg);
        }

        /* 瀑布流区域 */
        .waterfall-section {
            padding-bottom: 60px;
        }

        .waterfall-header {
            text-align: center;
            margin-bottom: 30px;
        }

        .waterfall-title {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--text-color);
            margin: 0;
        }

        .waterfall-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }

        @media (max-width: 900px) {
            .waterfall-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 600px) {
            .waterfall-grid {
                grid-template-columns: 1fr;
            }
            .hero-stats {
                gap: 24px;
            }
            .hero-stat-number {
                font-size: 1.6rem;
            }
        }

        /* 卡片样式 */
        .card {
            background: #fff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            transition: all 0.2s;
            text-decoration: none;
            color: inherit;
            display: block;
        }

        .card:hover {
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .card-issue {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-color);
        }

        .card-time {
            font-size: 0.8rem;
            color: var(--sub-text);
        }

        .card-summary {
            font-size: 0.9rem;
            color: var(--text-color);
            line-height: 1.6;
            margin-bottom: 12px;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-logos {
            display: flex;
            gap: 6px;
        }

        .card-logo {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            object-fit: contain;
            background: #f5f5f5;
            padding: 2px;
        }

        .card-count {
            font-size: 0.8rem;
            color: var(--sub-text);
        }

        /* 加载指示器 */
        .loading-indicator {
            text-align: center;
            padding: 30px;
            color: var(--sub-text);
            font-size: 0.9rem;
        }

        .loading-indicator.hidden {
            display: none;
        }

        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid var(--border-color);
            border-top-color: var(--text-color);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .no-more {
            text-align: center;
            padding: 30px;
            color: var(--sub-text);
            font-size: 0.85rem;
        }

        /* 页脚 */
        .landing-footer {
            text-align: center;
            padding: 40px 20px;
            border-top: 1px solid var(--border-color);
            color: var(--sub-text);
            font-size: 0.85rem;
        }

        .landing-footer a {
            color: var(--sub-text);
            text-decoration: none;
        }

        .landing-footer a:hover {
            color: var(--text-color);
        }

        .footer-links-landing {
            margin-top: 12px;
        }

        .footer-links-landing a {
            margin: 0 12px;
        }
    </style>
</head>
<body>

    <div class="landing-wrapper">
        <!-- Hero 区域 -->
        <section class="hero">
            <img src="images/avatar-placeholder.svg" alt="大黑" class="hero-avatar">
            <h1 class="hero-title">大黑AI速报</h1>
            <p class="hero-subtitle">每 4 小时自动更新的 AI 行业快讯</p>

            <div class="hero-stats">
                <div class="hero-stat">
                    <div class="hero-stat-number"><?php echo $latest_issue; ?></div>
                    <div class="hero-stat-label">已更新期数</div>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-number">4h</div>
                    <div class="hero-stat-label">更新频率</div>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-number">5</div>
                    <div class="hero-stat-label">内容分类</div>
                </div>
            </div>

            <div class="hero-buttons">
                <a href="realtime.php" class="hero-btn hero-btn-primary">查看最新一期</a>
                <a href="changelog.php" class="hero-btn hero-btn-secondary">AI工具速报</a>
                <a href="rss.php" class="hero-btn hero-btn-secondary" target="_blank">RSS 订阅</a>
                <a href="https://daheiai.com" class="hero-btn hero-btn-secondary" target="_blank">大黑的主页</a>
            </div>
        </section>

        <!-- 瀑布流区域 -->
        <section class="waterfall-section">
            <div class="waterfall-header">
                <h2 class="waterfall-title">往期速报</h2>
            </div>

            <div class="waterfall-grid" id="waterfall-grid">
                <?php foreach ($cards as $card): ?>
                <a href="realtime.php?file=<?php echo htmlspecialchars($card['filename']); ?>" class="card">
                    <div class="card-header">
                        <span class="card-issue">第 <?php echo htmlspecialchars($card['issue_number']); ?> 期</span>
                        <span class="card-time"><?php echo htmlspecialchars($card['date']); ?> <?php echo htmlspecialchars($card['time']); ?></span>
                    </div>
                    <div class="card-summary"><?php echo htmlspecialchars($card['summary']); ?></div>
                    <div class="card-footer">
                        <div class="card-logos">
                            <?php foreach ($card['brand_logos'] as $bl): ?>
                            <img src="<?php echo htmlspecialchars($bl['logo']); ?>"
                                 alt="<?php echo htmlspecialchars($bl['brand']); ?>"
                                 class="card-logo">
                            <?php endforeach; ?>
                        </div>
                        <span class="card-count"><?php echo $card['item_count']; ?> 条快讯</span>
                    </div>
                </a>
                <?php endforeach; ?>
            </div>

            <!-- 加载指示器 -->
            <div class="loading-indicator hidden" id="loading-indicator">
                <span class="loading-spinner"></span>加载中...
            </div>

            <!-- 没有更多 -->
            <div class="no-more hidden" id="no-more">已经到底啦</div>
        </section>

        <!-- 页脚 -->
        <footer class="landing-footer">
            <div>由 <a href="https://daheiai.com/" target="_blank">人工大黑</a> 制作</div>
            <div class="footer-links-landing">
                <a href="history.php">全部历史</a>
                <a href="rss.php" target="_blank">RSS 订阅</a>
            </div>
        </footer>
    </div>

    <script>
    (function() {
        // 无限滚动加载
        const grid = document.getElementById('waterfall-grid');
        const loadingIndicator = document.getElementById('loading-indicator');
        const noMore = document.getElementById('no-more');

        let offset = <?php echo $initial_count; ?>;
        let loading = false;
        let hasMore = <?php echo $has_more ? 'true' : 'false'; ?>;
        const limit = 20;

        // 创建卡片 HTML
        function createCardHTML(card) {
            let logosHTML = '';
            if (card.brand_logos && card.brand_logos.length > 0) {
                logosHTML = card.brand_logos.map(bl =>
                    `<img src="${escapeHtml(bl.logo)}" alt="${escapeHtml(bl.brand)}" class="card-logo">`
                ).join('');
            }

            return `
                <a href="realtime.php?file=${encodeURIComponent(card.filename)}" class="card">
                    <div class="card-header">
                        <span class="card-issue">第 ${escapeHtml(card.issue_number)} 期</span>
                        <span class="card-time">${escapeHtml(card.date)} ${escapeHtml(card.time)}</span>
                    </div>
                    <div class="card-summary">${escapeHtml(card.summary)}</div>
                    <div class="card-footer">
                        <div class="card-logos">${logosHTML}</div>
                        <span class="card-count">${card.item_count} 条快讯</span>
                    </div>
                </a>
            `;
        }

        // HTML 转义
        function escapeHtml(text) {
            if (text === null || text === undefined) return '';
            const div = document.createElement('div');
            div.textContent = String(text);
            return div.innerHTML;
        }

        // 加载更多
        async function loadMore() {
            if (loading || !hasMore) return;

            loading = true;
            loadingIndicator.classList.remove('hidden');

            try {
                const response = await fetch(`api/cards.php?offset=${offset}&limit=${limit}`);
                const result = await response.json();

                if (result.success && result.data.length > 0) {
                    result.data.forEach(card => {
                        grid.insertAdjacentHTML('beforeend', createCardHTML(card));
                    });

                    offset += result.data.length;
                    hasMore = result.meta.has_more;
                }

                if (!hasMore) {
                    noMore.classList.remove('hidden');
                }
            } catch (error) {
                console.error('加载失败:', error);
            } finally {
                loading = false;
                loadingIndicator.classList.add('hidden');
            }
        }

        // 滚动检测
        function checkScroll() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const windowHeight = window.innerHeight;
            const docHeight = document.documentElement.scrollHeight;

            // 距离底部 300px 时开始加载
            if (scrollTop + windowHeight >= docHeight - 300) {
                loadMore();
            }
        }

        // 节流
        let scrollTimer = null;
        window.addEventListener('scroll', function() {
            if (scrollTimer) return;
            scrollTimer = setTimeout(function() {
                scrollTimer = null;
                checkScroll();
            }, 100);
        });

        // 初始检查（如果页面不够长）
        if (!hasMore) {
            noMore.classList.remove('hidden');
        } else {
            checkScroll();
        }
    })();
    </script>

<script> var _mtj = _mtj || []; (function () { var mtj = document.createElement("script"); mtj.src = "https://node96.aizhantj.com:21233/tjjs/?k=qk25ajlrkia"; var s = document.getElementsByTagName("script")[0]; s.parentNode.insertBefore(mtj, s); })(); </script>
</body>
</html>
