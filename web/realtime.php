<?php
/**
 * AI 快讯网页渲染
 * 简约报刊风格
 */

require_once __DIR__ . '/config.php';

// 支持通过 URL 参数加载历史版本
$file_param = $_GET['file'] ?? null;
if ($file_param && preg_match('/^quick_\d{4}-\d{2}-\d{2}_\d{4}$/', $file_param)) {
    // 加载指定的历史文件
    $data = load_quick_data($file_param . '.json');
} else {
    // 加载最新版本
    $data = load_quick_data();
}

if (!$data) {
    die('无法加载数据');
}

// 按分类分组
$grouped_items = [];
foreach ($data['items'] as $item) {
    $cat = $item['category'] ?? 'industry';
    if (!isset($grouped_items[$cat])) {
        $grouped_items[$cat] = [];
    }
    $grouped_items[$cat][] = $item;
}

// 分类排序优先级
$category_order = ['model', 'product', 'tutorial', 'hardware', 'industry'];

// 收集本期所有提到的品牌（用于 Banner）
$all_brands = [];
foreach ($data['items'] as $item) {
    if (!empty($item['brands'])) {
        foreach ($item['brands'] as $brand) {
            if (!in_array($brand, $all_brands)) {
                $all_brands[] = $brand;
            }
        }
    }
}
// 取前8个品牌用于背景展示
$banner_brands = array_slice($all_brands, 0, 8);

// 格式化日期时间显示
$date_display = date('Y-m-d');
$time_display = date('H:i');
if (!empty($data['generated_at'])) {
    $dt = DateTime::createFromFormat('Y-m-d H:i:s', $data['generated_at']);
    if ($dt) {
        $date_display = $dt->format('Y-m-d');
        $time_display = $dt->format('H:i');
    }
}

// 期数
$issue_number = $data['issue_number'] ?? 504;

// 信源统计
$twitter_count = $data['source_stats']['twitter'] ?? 0;
$rss_count = $data['source_stats']['rss'] ?? 0;

/**
 * 格式化品牌名用于显示
 */
function format_brand_name($brand) {
    $special = [
        'openai' => 'OpenAI',
        'deepseek' => 'DeepSeek',
        'chatglm' => 'ChatGLM',
        'huggingface' => 'HuggingFace',
        'xai' => 'xAI',
        'minimax' => 'MiniMax',
        'github' => 'GitHub',
        'nvidia' => 'NVIDIA',
        'zhipu' => 'Zhipu',
        'qwen' => 'Qwen',
        'kimi' => 'Kimi',
        'claude' => 'Claude',
        'gemini' => 'Gemini',
        'mistral' => 'Mistral',
        'meta' => 'Meta',
        'bytedance' => 'ByteDance',
        'alibaba' => 'Alibaba',
    ];

    if (isset($special[strtolower($brand)])) {
        return $special[strtolower($brand)];
    }
    return ucfirst($brand);
}

/**
 * 处理文本中的【】标记，转换为高亮
 */
function render_highlights($text) {
    // 将【xxx】转换为 <strong>xxx</strong>
    return preg_replace('/【([^】]+)】/', '<strong>$1</strong>', htmlspecialchars($text));
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大黑AI速报</title>
    <link rel="stylesheet" href="css/style.css">
    <link rel="alternate" type="application/rss+xml" title="大黑AI速报 RSS" href="rss.php">
</head>
<body>

    <div class="mobile-wrapper">
        <!-- 顶部 Banner -->
        <header class="banner">
            <!-- 背景 Logo（景深模糊）-->
            <div class="banner-bg-logos-img">
                <?php foreach ($banner_brands as $brand):
                    $logo_url = get_brand_logo($brand);
                    if ($logo_url):
                ?>
                <img src="<?php echo htmlspecialchars($logo_url); ?>"
                     alt="<?php echo htmlspecialchars($brand); ?>"
                     class="banner-logo-blur">
                <?php
                    endif;
                endforeach;
                ?>
            </div>

            <!-- 背景品牌文字 -->
            <div class="banner-bg-logos">
                <?php foreach ($banner_brands as $brand): ?>
                <span><?php echo htmlspecialchars(format_brand_name($brand)); ?></span>
                <?php endforeach; ?>
            </div>

            <!-- 右下角信息 -->
            <div class="banner-info">
                <img src="images/avatar-placeholder.svg" alt="大黑" class="banner-avatar">
                <h1 class="banner-title">大黑AI速报</h1>
                <p class="banner-date"><?php echo htmlspecialchars($date_display); ?> <?php echo htmlspecialchars($time_display); ?> · 第<?php echo $issue_number; ?>期</p>
            </div>
        </header>

        <!-- AI 总结 -->
        <?php if (!empty($data['summary'])): ?>
        <section class="ai-summary">
            <span class="section-label">◆ AI 总结</span>
            <p class="summary-content"><?php echo render_highlights($data['summary']); ?></p>
        </section>
        <?php endif; ?>

        <!-- 分类内容 -->
        <?php
        foreach ($category_order as $cat_key) {
            if (!isset($grouped_items[$cat_key]) || empty($grouped_items[$cat_key])) {
                continue;
            }

            $cat_info = get_category_info($cat_key);
            $items = $grouped_items[$cat_key];
        ?>
        <section class="content-block">
            <h2 class="category-header"><?php echo htmlspecialchars($cat_info['name']); ?></h2>

            <?php foreach ($items as $item): ?>
            <article class="article-item">
                <!-- Logo + 品牌关键词 -->
                <?php if (!empty($item['brands'])): ?>
                <div class="article-meta">
                    <div class="article-logos">
                        <?php foreach (array_slice($item['brands'], 0, 3) as $brand):
                            $logo_url = get_brand_logo($brand);
                            if ($logo_url):
                        ?>
                        <img src="<?php echo htmlspecialchars($logo_url); ?>"
                             alt="<?php echo htmlspecialchars($brand); ?>"
                             class="article-logo">
                        <?php
                            endif;
                        endforeach;
                        ?>
                    </div>
                    <span class="article-keywords">
                        <?php echo htmlspecialchars(implode(' / ', array_map('format_brand_name', array_slice($item['brands'], 0, 3)))); ?>
                    </span>
                </div>
                <?php endif; ?>

                <!-- 标题 -->
                <h3 class="article-title"><?php echo render_highlights($item['title']); ?></h3>

                <!-- 内容 -->
                <div class="article-body">
                    <?php echo render_highlights($item['content']); ?>
                </div>
            </article>
            <?php endforeach; ?>
        </section>
        <?php } ?>

        <!-- 页脚 -->
        <footer class="footer">
            <div>由<a href="https://daheiai.com/" target="_blank" class="footer-link-subtle">人工大黑</a>制作</div>
            <div class="footer-source">
                经由 <?php echo $twitter_count; ?> 条推特信源、<?php echo $rss_count; ?> 条RSS信源生成
            </div>
            <div class="footer-source">
                访问 news.daheiai.com 在线查看本期日报
            </div>
            <div class="footer-links">
                <a href="history.php">历史期刊</a>
                <a onclick="document.getElementById('sources-panel').classList.toggle('active')">查看本期来源</a>
                <a href="rss.php" target="_blank">RSS 订阅</a>
            </div>
            <?php if (!empty($data['all_sources'])): ?>
            <div id="sources-panel" class="sources-panel">
                <div class="sources-panel-title">本期来源（共 <?php echo count($data['all_sources']); ?> 条）</div>
                <?php foreach ($data['all_sources'] as $src): ?>
                <div class="source-item">
                    <span class="source-type"><?php echo $src['source_type'] === 'twitter' ? '推特' : 'RSS'; ?></span>
                    <span class="source-author"><?php echo htmlspecialchars($src['author']); ?></span>
                    <span class="source-snippet"><?php echo htmlspecialchars($src['snippet']); ?></span>
                    <a href="<?php echo htmlspecialchars($src['url']); ?>" target="_blank">查看原文</a>
                </div>
                <?php endforeach; ?>
            </div>
            <?php endif; ?>
        </footer>
    </div>

</body>
</html>
