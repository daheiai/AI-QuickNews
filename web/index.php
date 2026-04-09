<?php
/**
 * AI 快讯网页渲染
 * 用于 Selenium 截图
 */

require_once __DIR__ . '/config.php';

// 加载数据
$data = load_quick_data();

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
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大黑4小时AI速报</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <!-- 页头 -->
        <header class="header">
            <div class="header-content">
                <img src="images/avatar-placeholder.svg" alt="AI QuickNews" class="header-avatar" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover;">
                <div class="header-text">
                    <h1 class="header-title">大黑4小时AI速报</h1>
                    <div class="header-date">
                        <svg class="date-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                            <line x1="16" y1="2" x2="16" y2="6"/>
                            <line x1="8" y1="2" x2="8" y2="6"/>
                            <line x1="3" y1="10" x2="21" y2="10"/>
                        </svg>
                        <span><?php echo htmlspecialchars($data['generated_at'] ?? date('Y-m-d H:i')); ?></span>
                    </div>
                </div>
            </div>
        </header>

        <!-- AI 总结区域 -->
        <?php if (!empty($data['summary'])): ?>
        <section class="summary-section">
            <div class="summary-label">AI 总结</div>
            <p class="summary-text"><?php echo htmlspecialchars($data['summary']); ?></p>
        </section>
        <?php endif; ?>

        <!-- 主内容区 -->
        <main class="main-content">
            <?php
            // 按分类顺序输出
            foreach ($category_order as $cat_key) {
                if (!isset($grouped_items[$cat_key]) || empty($grouped_items[$cat_key])) {
                    continue;
                }

                $cat_info = get_category_info($cat_key);
                $items = $grouped_items[$cat_key];
            ?>
            <section class="category-section">
                <div class="category-header">
                    <span class="category-dot" style="background-color: <?php echo $cat_info['color']; ?>"></span>
                    <h2 class="category-title"><?php echo htmlspecialchars($cat_info['name']); ?></h2>
                    <span class="category-count"><?php echo count($items); ?></span>
                </div>

                <div class="news-list">
                    <?php foreach ($items as $item): ?>
                    <article class="news-card">
                        <!-- Logo 和标签区域 -->
                        <div class="card-meta">
                            <?php if (!empty($item['brands'])): ?>
                            <div class="brand-logos">
                                <?php foreach (array_slice($item['brands'], 0, 3) as $brand): ?>
                                    <?php $logo_url = get_brand_logo($brand); ?>
                                    <?php if ($logo_url): ?>
                                    <img src="<?php echo htmlspecialchars($logo_url); ?>"
                                         alt="<?php echo htmlspecialchars($brand); ?>"
                                         class="brand-logo">
                                    <?php endif; ?>
                                <?php endforeach; ?>
                            </div>
                            <div class="brand-tags">
                                <?php foreach (array_slice($item['brands'], 0, 4) as $brand): ?>
                                    <?php $color = get_brand_color($brand); ?>
                                    <span class="brand-tag"
                                          style="background-color: <?php echo $color['bg']; ?>; color: <?php echo $color['text']; ?>">
                                        <?php echo htmlspecialchars(ucfirst($brand)); ?>
                                    </span>
                                <?php endforeach; ?>
                            </div>
                            <?php endif; ?>
                        </div>

                        <!-- 标题 -->
                        <h3 class="news-title"><?php echo htmlspecialchars($item['title']); ?></h3>

                        <!-- 内容 -->
                        <p class="news-content"><?php echo htmlspecialchars($item['content']); ?></p>
                    </article>
                    <?php endforeach; ?>
                </div>
            </section>
            <?php } ?>
        </main>

        <!-- 页脚 -->
        <footer class="footer">
            <div class="footer-content">
                <p class="footer-desc">由人工大黑制作</p>
            </div>
        </footer>
    </div>
</body>
</html>
