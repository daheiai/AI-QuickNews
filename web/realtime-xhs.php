<?php
/**
 * AI 快讯网页渲染 - 小红书版
 * 固定 768x1100 容器，支持智能分页
 */

require_once __DIR__ . '/config.php';

// 支持通过 URL 参数加载历史版本
$file_param = $_GET['file'] ?? null;
if ($file_param && preg_match('/^quick_\d{4}-\d{2}-\d{2}_\d{4}$/', $file_param)) {
    $data = load_quick_data($file_param . '.json');
} else {
    $data = load_quick_data();
}

if (!$data) {
    die('无法加载数据');
}

// 分页参数
$page_num = isset($_GET['page']) ? intval($_GET['page']) : 1;

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

// 收集本期所有品牌（用于 Banner）
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
$banner_brands = array_slice($all_brands, 0, 8);

// 格式化日期时间
$date_display = date('Y-m-d');
$time_display = date('H:i');
if (!empty($data['generated_at'])) {
    $dt = DateTime::createFromFormat('Y-m-d H:i:s', $data['generated_at']);
    if ($dt) {
        $date_display = $dt->format('Y-m-d');
        $time_display = $dt->format('H:i');
    }
}

$issue_number = $data['issue_number'] ?? 504;

// 信源统计
$twitter_count = $data['source_stats']['twitter'] ?? 0;
$rss_count = $data['source_stats']['rss'] ?? 0;

// 信源编号
$source_index_map = [];
$current_index = 1;
foreach ($data['items'] as $item) {
    if (!empty($item['sources'])) {
        foreach ($item['sources'] as $src) {
            $url = $src['url'];
            if (!isset($source_index_map[$url])) {
                $source_index_map[$url] = $current_index;
                $current_index++;
            }
        }
    }
}

// 构建页面分组（改进的智能分页）
$header_height = 220;
$summary_height = !empty($data['summary']) ? 100 : 0;
$footer_height = 80;
$content_max_height = 1100 - $header_height - $footer_height; // 800px

// 将所有新闻拆分成单条,保留分类信息
$all_items_list = [];
foreach ($category_order as $cat_key) {
    if (!isset($grouped_items[$cat_key]) || empty($grouped_items[$cat_key])) {
        continue;
    }

    $cat_info = get_category_info($cat_key);
    foreach ($grouped_items[$cat_key] as $item) {
        // 估算单条新闻高度
        $content_len = mb_strlen($item['content'] ?? '', 'utf-8');
        $title_len = mb_strlen($item['title'] ?? '', 'utf-8');
        $content_lines = ceil($content_len / 45);
        $title_lines = ceil($title_len / 35);
        $item_height = 60 + ($content_lines + $title_lines) * 24 + 30; // 标题+品牌+内容+间距

        $all_items_list[] = [
            'cat_key' => $cat_key,
            'cat_name' => $cat_info['name'],
            'item' => $item,
            'height' => $item_height
        ];
    }
}

// 统计总高度
$total_items_height = 0;
foreach ($all_items_list as $it) {
    $total_items_height += $it['height'];
}
$total_content_height = $summary_height + $total_items_height;

// 如果总内容高度不超过单页高度,只生成1页
if ($total_content_height <= $content_max_height) {
    // 合并同类项
    $pages = [[
        'items' => [],
        'height' => $header_height + $summary_height,
        'last_cat' => null
    ]];
    foreach ($all_items_list as $it) {
        $pages[0]['items'][] = $it;
        $pages[0]['height'] += $it['height'];
    }
} else {
    // 多页分配 - 按单条新闻分配,确保不被截断
    $pages = [];

    // 第1页 = 封面 + AI总结
    $page_build = [
        'items' => [],
        'height' => $header_height + $summary_height,
        'last_cat' => null
    ];

    $last_cat_key = null; // 跟踪上一个分类

    foreach ($all_items_list as $it) {
        $cat_key = $it['cat_key'];

        // 检查是否需要新开分类标题
        $need_new_category = ($last_cat_key !== $cat_key);
        $category_header_height = $need_new_category ? 50 : 0;
        $last_cat_key = $cat_key;

        $next_height = $page_build['height'] + $category_header_height + $it['height'];

        // 如果当前页为空,必须放入
        // 如果放入后不超过最大高度,可以放入
        // 否则新开一页
        if (empty($page_build['items']) || $next_height <= $content_max_height) {
            if ($need_new_category && !empty($page_build['items'])) {
                // 添加分类标题高度
                $page_build['height'] += $category_header_height;
            }
            $page_build['items'][] = $it;
            $page_build['height'] = $next_height;
            $page_build['last_cat'] = $cat_key;
        } else {
            // 保存当前页,开启新页
            $pages[] = $page_build;
            $page_build = [
                'items' => [$it],
                'height' => $header_height + $category_header_height + $it['height'],
                'last_cat' => $cat_key
            ];
        }
    }

    // 保存最后一页
    if (!empty($page_build['items'])) {
        $pages[] = $page_build;
    }
}

$total_pages = count($pages);
if ($page_num > $total_pages) $page_num = $total_pages;
if ($page_num < 1) $page_num = 1;
$page_data = $pages[$page_num - 1];

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
    return preg_replace('/【([^】]+)】/', '<strong>$1</strong>', htmlspecialchars($text));
}
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大黑AI速报</title>
    <link rel="stylesheet" href="css/realtime-xhs.css">
</head>
<body>

    <div class="xhs-wrapper">
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

        <!-- AI 总结 (仅第1页显示) -->
        <?php if ($page_num == 1 && !empty($data['summary'])): ?>
        <section class="ai-summary">
            <span class="section-label">◆ AI 总结</span>
            <p class="summary-content"><?php echo render_highlights($data['summary']); ?></p>
        </section>
        <?php endif; ?>

        <!-- 分类内容 -->
        <?php
        // 预处理:按分类分组
        $items_by_cat = [];
        if (!empty($page_data['items'])) {
            foreach ($page_data['items'] as $it) {
                $cat_key = $it['cat_key'];
                if (!isset($items_by_cat[$cat_key])) {
                    $items_by_cat[$cat_key] = [
                        'name' => $it['cat_name'],
                        'items' => []
                    ];
                }
                $items_by_cat[$cat_key]['items'][] = $it['item'];
            }
        }

        // 渲染
        if (!empty($items_by_cat)) {
            foreach ($items_by_cat as $cat_key => $cat_data) {
                echo '<section class="content-block">';
                echo '<h2 class="category-header">' . htmlspecialchars($cat_data['name']) . '</h2>';

                foreach ($cat_data['items'] as $item) {
                    echo '<article class="article-item">';

                    // 品牌
                    if (!empty($item['brands'])) {
                        echo '<div class="article-meta"><div class="article-logos">';
                        foreach (array_slice($item['brands'], 0, 3) as $brand) {
                            $logo_url = get_brand_logo($brand);
                            if ($logo_url) {
                                echo '<img src="' . htmlspecialchars($logo_url) . '" alt="' . htmlspecialchars($brand) . '" class="article-logo">';
                            }
                        }
                        echo '</div><span class="article-keywords">' . htmlspecialchars(implode(' / ', array_map('format_brand_name', array_slice($item['brands'], 0, 3)))) . '</span></div>';
                    }

                    // 标题
                    echo '<h3 class="article-title">' . render_highlights($item['title']) . '</h3>';

                    // 内容
                    echo '<div class="article-body">';
                    echo render_highlights($item['content']);
                    if (!empty($item['sources'])) {
                        foreach ($item['sources'] as $src) {
                            $idx = $source_index_map[$src['url']];
                            echo '<sup><a href="' . htmlspecialchars($src['url']) . '" target="_blank" class="ref-link">[' . $idx . ']</a></sup>';
                        }
                    }
                    echo '</div>';
                    echo '</article>';
                }

                echo '</section>';
            }
        }
        ?>

        <!-- 页脚 -->
        <footer class="footer">
            <div>由<a href="https://daheiai.com/" target="_blank" class="footer-link-subtle">人工大黑</a>制作</div>
            <div class="footer-source">
                经由 <?php echo $twitter_count; ?> 条推特信源、<?php echo $rss_count; ?> 条RSS信源生成
            </div>
            <div class="footer-xhs-link">查信源→news.daheiai点康姆</div>
            <div class="footer-pagination">
                <span class="page-num"><?php echo $page_num; ?></span>
                <span class="page-divider">/</span>
                <span class="page-total"><?php echo $total_pages; ?></span>
            </div>
        </footer>
    </div>

</body>
</html>
