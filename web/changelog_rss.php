<?php
/**
 * AI 工具更新日志 RSS Feed
 */
require_once __DIR__ . '/config.php';

$site_title = '大黑AI工具速报';
$site_description = 'AI 编程工具版本更新追踪，中文翻译，涵盖 Claude Code、OpenCode、Gemini CLI 等。';
$site_url = 'https://news.daheiai.com';
$site_language = 'zh-cn';

$data = load_changelog_data();
$trends = load_changelog_trend();

header('Content-Type: application/rss+xml; charset=UTF-8');
header('Cache-Control: max-age=3600');

echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title><?php echo htmlspecialchars($site_title); ?></title>
        <link><?php echo htmlspecialchars($site_url . '/changelog.php'); ?></link>
        <description><?php echo htmlspecialchars($site_description); ?></description>
        <language><?php echo $site_language; ?></language>
        <lastBuildDate><?php echo date('r'); ?></lastBuildDate>
        <atom:link href="<?php echo htmlspecialchars($site_url . '/changelog_rss.php'); ?>" rel="self" type="application/rss+xml"/>
        <ttl>720</ttl>
<?php
if ($data && !empty($data['repos'])) {
    $repo_order = ['Claude Code', 'OpenCode', 'OpenClaw', 'Gemini CLI', 'Codex'];
    foreach ($repo_order as $name) {
        $repo = $data['repos'][$name] ?? null;
        if (!$repo || empty($repo['releases'])) continue;

        // 每个仓库最近 20 条
        $releases = array_slice($repo['releases'], 0, 20);
        foreach ($releases as $r) {
            $tag = $r['tag_name'] ?? '';
            $body_cn = $r['body_cn'] ?? '';
            $body_en = $r['body_en'] ?? '';
            $url = $r['url'] ?? '';
            $published = $r['published_at'] ?? '';
            $id = $r['id'] ?? '';
            $is_pre = !empty($r['is_prerelease']);

            $title = $name . ' ' . $tag;
            if ($is_pre) $title .= ' (预发布)';

            // 纯文本描述：取前 200 字
            $desc = mb_substr(strip_tags($body_cn ?: $body_en), 0, 200, 'UTF-8');

            // HTML 内容
            $content_html = '';
            if ($body_cn) {
                $content_html .= '<h3>中文</h3>';
                $content_html .= '<pre>' . htmlspecialchars($body_cn) . '</pre>';
            }
            if ($body_en) {
                $content_html .= '<h3>English</h3>';
                $content_html .= '<pre>' . htmlspecialchars($body_en) . '</pre>';
            }
            $detail_url = $site_url . '/changelog_detail.php?id=' . urlencode($id);
            $content_html .= '<p><a href="' . htmlspecialchars($detail_url) . '">查看详情</a>';
            if ($url) {
                $content_html .= ' | <a href="' . htmlspecialchars($url) . '">GitHub 原文</a>';
            }
            $content_html .= '</p>';

            $pub_date = $published ? date('r', strtotime($published)) : date('r');
            $guid = $site_url . '/changelog/' . urlencode($id);
?>
        <item>
            <title><?php echo htmlspecialchars($title); ?></title>
            <link><?php echo htmlspecialchars($detail_url); ?></link>
            <description><?php echo htmlspecialchars($desc); ?></description>
            <content:encoded><![CDATA[<?php echo $content_html; ?>]]></content:encoded>
            <pubDate><?php echo $pub_date; ?></pubDate>
            <guid isPermaLink="false"><?php echo htmlspecialchars($guid); ?></guid>
            <category><?php echo htmlspecialchars($name); ?></category>
        </item>
<?php
        }
    }
}
?>
    </channel>
</rss>
