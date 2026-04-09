<?php
/**
 * 信源展示页面
 * 展示项目关注的所有 Twitter 账号和 RSS 源
 */

require_once __DIR__ . '/config.php';

// 解析 Twitter 用户名
$twitter_usernames = explode(',', 'karminski3,op7418,Alibaba_Qwen,arena,MiniMax_AI,KwaiAICoder,Zai_org,JustinLin610,lmstudio,oran_ge,deepseek_ai,OpenRouterAI,xiaohu,AnthropicAI,OpenAI,huggingface,Kimi_Moonshot,Hx1u0,Ali_TongyiLab,cline,OpenAIDevs,cerebras,Baidu_Inc,ManusAI,vista8,geekbb');

// Twitter 账号分类
$twitter_categories = [
    'ai_companies' => [
        'name' => 'AI 公司官方',
        'accounts' => ['Alibaba_Qwen', 'MiniMax_AI', 'deepseek_ai', 'OpenRouterAI', 'AnthropicAI', 'OpenAI', 'huggingface', 'Kimi_Moonshot', 'Ali_TongyiLab', 'OpenAIDevs', 'cerebras', 'Baidu_Inc', 'ManusAI']
    ],
    'individuals' => [
        'name' => '个人账号',
        'accounts' => ['karminski3', 'op7418', 'KwaiAICoder', 'JustinLin610', 'lmstudio', 'oran_ge', 'xiaohu', 'Hx1u0', 'cline', 'vista8', 'geekbb']
    ],
    'platforms' => [
        'name' => '平台与社区',
        'accounts' => ['arena', 'Zai_org']
    ]
];

// RSS 源分类
$rss_categories = [
    'media' => [
        'name' => '技术媒体与博客',
        'icon' => '@',
        'feeds' => []
    ],
    'twitter_rss' => [
        'name' => 'Twitter 转 RSS',
        'icon' => '@',
        'feeds' => []
    ],
    'ai_tools' => [
        'name' => 'AI 工具与框架',
        'icon' => '@',
        'feeds' => []
    ],
    'investors' => [
        'name' => '投资人与行业领袖',
        'icon' => '@',
        'feeds' => []
    ],
    'tech_blogs' => [
        'name' => '技术博客',
        'icon' => '@',
        'feeds' => []
    ],
    'youtube' => [
        'name' => 'YouTube 频道',
        'icon' => '@',
        'feeds' => []
    ],
    'wechat' => [
        'name' => '微信公众号',
        'icon' => '@',
        'feeds' => []
    ]
];

// 读取 RSS feeds 配置
$rss_feeds_file = PROJECT_ROOT . '/resources/rss_feeds.json';
$rss_feeds = [];
if (file_exists($rss_feeds_file)) {
    $rss_feeds = json_decode(file_get_contents($rss_feeds_file), true) ?? [];
}

// 分类 RSS feeds
foreach ($rss_feeds as $feed) {
    $name = $feed['name'];
    $url = $feed['url'];
    $weight = $feed['weight'] ?? 1.0;

    // 技术媒体与博客
    if (in_array($name, ['量子位', '宝玉的分享', '掘金本周最热', 'deeplearning.ai', '腾讯技术工程', 'ByteByteGo Newsletter', 'Google Cloud Blog', 'Linux.do', 'Last Week in AI'])) {
        $rss_categories['media']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
    // AI 公司官方 Twitter
    elseif (strpos($name, 'OpenAI(') !== false || strpos($name, 'Anthropic(') !== false || strpos($name, 'Google') !== false ||
            strpos($name, 'Microsoft') !== false || strpos($name, 'NVIDIA') !== false || strpos($name, 'Hugging') !== false ||
            strpos($name, 'Qwen(') !== false || strpos($name, 'Cognition') !== false || strpos($name, 'Fei-Fei') !== false ||
            strpos($name, 'Stanford') !== false || strpos($name, 'a16z') !== false || strpos($name, 'Y Combinator') !== false) {
        $rss_categories['twitter_rss']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
    // AI 工具与框架
    elseif (in_array($name, ['LangChain(@LangChainAI)', 'LlamaIndex(@llama_index)', 'Cursor(@cursor_ai)', 'Fireworks AI(@FireworksAI_HQ)', 'ElevenLabs(@elevenlabsio)', 'Browser Use(@browser_use)', 'lmarena.ai(@lmarena_ai)', 'ManusAI(@ManusAI_HQ)', 'Hailuo AI/MiniMax(@Hailuo_AI)', 'Runway(@runwayml)'])) {
        $rss_categories['ai_tools']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
    // 投资人与行业领袖
    elseif (in_array($name, ['Simon Willison(@simonw)', 'Jerry Liu(@jerryjliu0)', 'Harrison Chase(@hwchase17)', 'Justine Moore(@venturetwins)', 'Suhail(@Suhail)', 'Marc Andreessen(@pmarca)', 'Guillermo Rauch(@rauchg)', 'Paul Graham(@paulg)', 'Replicate(@replicate)', 'Weaviate(@weaviate_io)', 'Milvus(@milvusio)', 'Lenny Rachitsky(@lennysan)', 'Zara Zhang(@zarazhangrui)', 'Lee Robinson(@leerob)'])) {
        $rss_categories['investors']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
    // 技术博客
    elseif (in_array($name, ['Simon Willison\'s Weblog', 'Google DeepMind Blog', 'The Keyword (blog.google)', 'LangChain Blog', 'Anthropic News', 'Hugging Face Blog', 'ElevenLabs Blog', 'AWS Machine Learning Blog', 'The Cloudflare Blog', 'The GitHub Blog', 'Databricks', 'Stack Overflow Blog'])) {
        $rss_categories['tech_blogs']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
    // YouTube 频道
    elseif (in_array($name, ['Matt Wolfe', 'Matthew Berman'])) {
        $rss_categories['youtube']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
    // 微信公众号
    elseif (in_array($name, ['阿里云开发者', '数字生命卡兹克', '创业邦'])) {
        $rss_categories['wechat']['feeds'][] = ['name' => $name, 'url' => $url, 'weight' => $weight];
    }
}

// 统计数据
$total_twitter = count($twitter_usernames);
$total_rss = count($rss_feeds);
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>信源列表 - 大黑AI速报</title>
    <link rel="stylesheet" href="css/style.css">
    <style>
        .sources-wrapper {
            width: 390px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            background: var(--bg-color);
            box-shadow: 0 0 20px rgba(0,0,0,0.05);
        }

        /* 页面头部 */
        .sources-header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 30px;
        }

        .sources-header h1 {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 1.3rem;
            font-weight: 900;
            color: var(--text-color);
            margin: 0 0 8px 0;
        }

        .sources-header p {
            font-size: 0.85rem;
            color: var(--sub-text);
            margin: 0;
        }

        /* 统计卡片 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: var(--banner-bg);
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-number {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 1.8rem;
            font-weight: 900;
            color: var(--text-color);
        }

        .stat-label {
            font-size: 0.8rem;
            color: var(--sub-text);
            margin-top: 4px;
        }

        /* 分类区块 */
        .category-section {
            margin-bottom: 35px;
        }

        .category-title {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-color);
            border-left: 3px solid var(--accent-color);
            padding-left: 10px;
            margin-bottom: 16px;
        }

        .category-count {
            font-size: 0.75rem;
            color: var(--sub-text);
            font-weight: 400;
            margin-left: 8px;
        }

        /* 列表项 */
        .source-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .source-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }

        .source-item:last-child {
            border-bottom: none;
        }

        .source-item:hover {
            background: var(--banner-bg);
        }

        .source-name {
            font-size: 0.9rem;
            color: var(--text-color);
        }

        .source-meta {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .source-weight {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 3px;
            background: var(--banner-bg);
            color: var(--sub-text);
        }

        .source-weight.high {
            background: rgba(255, 107, 0, 0.15);
            color: var(--accent-color);
        }

        .source-link {
            color: var(--accent-color);
            text-decoration: none;
            font-size: 0.75rem;
        }

        .source-link:hover {
            text-decoration: underline;
        }

        /* Twitter 标签 */
        .twitter-tag {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            background: #f5f5f5;
            border-radius: 16px;
            margin: 4px;
            font-size: 0.85rem;
            color: var(--text-color);
        }

        .twitter-tag::before {
            content: '@';
            color: var(--sub-text);
            margin-right: 2px;
        }

        .twitter-tags {
            display: flex;
            flex-wrap: wrap;
            padding: 0 4px;
        }

        /* 返回链接 */
        .back-link {
            text-align: center;
            padding: 30px 0;
            border-top: 1px solid var(--border-color);
        }

        .back-link a {
            color: var(--sub-text);
            text-decoration: none;
            font-size: 0.85rem;
        }

        .back-link a:hover {
            color: var(--accent-color);
        }

        .back-link span {
            margin: 0 10px;
            color: var(--border-color);
        }

        /* 空状态 */
        .empty-state {
            text-align: center;
            padding: 30px;
            color: var(--sub-text);
            font-size: 0.85rem;
        }
    </style>
</head>
<body>

    <div class="sources-wrapper">
        <!-- 页面头部 -->
        <header class="sources-header">
            <h1>信源列表</h1>
            <p>我们关注的信息来源</p>
        </header>

        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number"><?php echo $total_twitter; ?></div>
                <div class="stat-label">Twitter 账号</div>
            </div>
            <div class="stat-card">
                <div class="stat-number"><?php echo $total_rss; ?></div>
                <div class="stat-label">RSS 源</div>
            </div>
        </div>

        <!-- Twitter 分类 -->
        <?php foreach ($twitter_categories as $cat_key => $category): ?>
        <?php if (empty($category['accounts'])) continue; ?>
        <section class="category-section">
            <h2 class="category-title">
                <?php echo htmlspecialchars($category['name']); ?>
                <span class="category-count"><?php echo count($category['accounts']); ?></span>
            </h2>
            <div class="twitter-tags">
                <?php foreach ($category['accounts'] as $account): ?>
                <span class="twitter-tag"><?php echo htmlspecialchars($account); ?></span>
                <?php endforeach; ?>
            </div>
        </section>
        <?php endforeach; ?>

        <!-- RSS 分类 -->
        <?php foreach ($rss_categories as $cat_key => $category): ?>
        <?php if (empty($category['feeds'])) continue; ?>
        <section class="category-section">
            <h2 class="category-title">
                <?php echo htmlspecialchars($category['name']); ?>
                <span class="category-count"><?php echo count($category['feeds']); ?></span>
            </h2>
            <ul class="source-list">
                <?php foreach ($category['feeds'] as $feed): ?>
                <li class="source-item">
                    <span class="source-name"><?php echo htmlspecialchars($feed['name']); ?></span>
                    <div class="source-meta">
                        <span class="source-weight <?php echo $feed['weight'] >= 2.5 ? 'high' : ''; ?>">
                            <?php echo $feed['weight']; ?>
                        </span>
                        <a href="<?php echo htmlspecialchars($feed['url']); ?>" target="_blank" class="source-link">访问</a>
                    </div>
                </li>
                <?php endforeach; ?>
            </ul>
        </section>
        <?php endforeach; ?>

        <!-- 返回链接 -->
        <div class="back-link">
            <a href="index.php">返回首页</a>
            <span>·</span>
            <a href="realtime.php">查看最新</a>
            <span>·</span>
            <a href="history.php">历史期刊</a>
            <span>·</span>
            <a href="rss.php" target="_blank">RSS 订阅</a>
        </div>
    </div>

<script> var _mtj = _mtj || []; (function () { var mtj = document.createElement("script"); mtj.src = "https://node96.aizhantj.com:21233/tjjs/?k=qk25ajlrkia"; var s = document.getElementsByTagName("script")[0]; s.parentNode.insertBefore(mtj, s); })(); </script>
</body>
</html>
