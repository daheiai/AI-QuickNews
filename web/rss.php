<?php
/**
 * AI 快讯 RSS Feed
 *
 * 访问地址: https://your-domain.com/rss.php
 * 或配置 URL 重写后: https://your-domain.com/feed.xml
 */

require_once __DIR__ . '/config.php';

// 网站配置
$site_title = '大黑AI速报';
$site_description = 'AI 行业快讯速报，每4小时更新一次，涵盖模型动态、产品工具、技巧教程、硬件动态、行业资讯。';
$site_url = 'https://news.daheiai.com';  // 请修改为你的实际域名
$site_language = 'zh-cn';

// 获取最近的速报列表（最多20期）
$history = get_history_list();
$feed_items = array_slice($history, 0, 20);

// 设置响应头
header('Content-Type: application/rss+xml; charset=UTF-8');
header('Cache-Control: max-age=1800'); // 缓存30分钟

// 生成 RSS XML
echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title><?php echo htmlspecialchars($site_title); ?></title>
        <link><?php echo htmlspecialchars($site_url); ?></link>
        <description><?php echo htmlspecialchars($site_description); ?></description>
        <language><?php echo $site_language; ?></language>
        <lastBuildDate><?php echo date('r'); ?></lastBuildDate>
        <atom:link href="<?php echo htmlspecialchars($site_url . '/rss.php'); ?>" rel="self" type="application/rss+xml"/>
        <image>
            <url><?php echo htmlspecialchars($site_url . '/images/avatar-placeholder.svg'); ?></url>
            <title><?php echo htmlspecialchars($site_title); ?></title>
            <link><?php echo htmlspecialchars($site_url); ?></link>
        </image>
        <ttl>240</ttl>
<?php
foreach ($feed_items as $item) {
    $filename = $item['filename'] . '.json';
    $data = load_quick_data($filename);

    if (!$data) continue;

    $issue_number = $data['issue_number'] ?? '?';
    $generated_at = $data['generated_at'] ?? '';
    $summary = $data['summary'] ?? '';
    $items = $data['items'] ?? [];

    // 构建标题
    $title = "第{$issue_number}期 - " . $item['date'] . ' ' . $item['time'];

    // 构建链接
    $link = $site_url . '/realtime.php?file=' . urlencode($item['filename']);

    // 构建描述（纯文本摘要）
    $description = strip_tags(str_replace(['【', '】'], ['[', ']'], $summary));

    // 构建完整内容（HTML格式）
    $content_html = '<h3>速报总结</h3>';
    $content_html .= '<p>' . htmlspecialchars(str_replace(['【', '】'], ['', ''], $summary)) . '</p>';

    if (!empty($items)) {
        $content_html .= '<h3>本期内容（共' . count($items) . '条）</h3>';
        $content_html .= '<ul>';
        foreach ($items as $news_item) {
            $category_name = $news_item['category_name'] ?? '资讯';
            $news_title = htmlspecialchars($news_item['title'] ?? '');
            $news_content = htmlspecialchars(str_replace(['【', '】'], ['', ''], $news_item['content'] ?? ''));

            $content_html .= '<li>';
            $content_html .= '<strong>[' . htmlspecialchars($category_name) . '] ' . $news_title . '</strong><br/>';
            $content_html .= $news_content;
            $content_html .= '</li>';
        }
        $content_html .= '</ul>';
    }

    $content_html .= '<p><a href="' . htmlspecialchars($link) . '">查看完整速报</a></p>';

    // 构建发布时间
    $pub_date = '';
    if ($generated_at) {
        $timestamp = strtotime($generated_at);
        if ($timestamp) {
            $pub_date = date('r', $timestamp);
        }
    }
    if (!$pub_date) {
        $pub_date = date('r', strtotime($item['date'] . ' ' . $item['time'] . ':00'));
    }

    // 构建 GUID
    $guid = $site_url . '/issue/' . $issue_number;
?>
        <item>
            <title><?php echo htmlspecialchars($title); ?></title>
            <link><?php echo htmlspecialchars($link); ?></link>
            <description><?php echo htmlspecialchars($description); ?></description>
            <content:encoded><![CDATA[<?php echo $content_html; ?>]]></content:encoded>
            <pubDate><?php echo $pub_date; ?></pubDate>
            <guid isPermaLink="false"><?php echo htmlspecialchars($guid); ?></guid>
            <category>AI快讯</category>
        </item>
<?php
}
?>
    </channel>
</rss>
