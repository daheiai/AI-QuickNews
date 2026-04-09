<?php
/**
 * Changelog 版本详情页
 * URL: changelog_detail.php?id=Claude+Code:288920711
 */
require_once __DIR__ . '/config.php';

$release_id = $_GET['id'] ?? '';
if (!$release_id) {
    die('缺少参数 id');
}

$data = load_changelog_data();
$result = find_release_by_id($data, $release_id);
if (!$result) {
    die('未找到该版本信息');
}

$repo = $result['repo'];
$release = $result['release'];
$repo_name = $repo['repo_name'];
$tag = $release['tag_name'];
$date = substr($release['published_at'] ?? '', 0, 10);
$url = $release['url'] ?? '';
$body_cn = $release['body_cn'] ?? '';
$body_en = $release['body_en'] ?? '';
$is_pre = !empty($release['is_prerelease']);
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars("$repo_name $tag"); ?> - 更新日志</title>
    <link rel="stylesheet" href="css/style.css">
    <link rel="stylesheet" href="css/changelog.css">
</head>
<body>

<div class="detail-wrapper">
    <div class="detail-header">
        <a href="changelog.php" class="detail-back">← 返回更新日志</a>
        <h1 class="detail-title">
            <?php echo htmlspecialchars($repo_name); ?>
            <span style="color: var(--accent-color);"><?php echo htmlspecialchars($tag); ?></span>
            <?php if ($is_pre): ?>
            <span class="card-tag" style="font-size:0.7rem;">预发布</span>
            <?php endif; ?>
        </h1>
        <div class="detail-meta">
            <?php echo htmlspecialchars($date); ?>
            <?php if ($url): ?>
             · <a href="<?php echo htmlspecialchars($url); ?>" target="_blank">GitHub 原文</a>
            <?php endif; ?>
        </div>
    </div>

    <div class="detail-content">
        <div class="lang-toggle">
            <button class="lang-btn active" id="detail-btn-cn" onclick="toggleDetailLang('cn')">中文</button>
            <button class="lang-btn" id="detail-btn-en" onclick="toggleDetailLang('en')">EN</button>
        </div>
        <div class="detail-body" id="detail-cn"><?php echo htmlspecialchars($body_cn ?: $body_en); ?></div>
        <div class="detail-body hidden" id="detail-en"><?php echo htmlspecialchars($body_en); ?></div>
    </div>

    <footer class="changelog-footer">
        <div>
            <a href="changelog.php">更新日志</a>
            <a href="index.php">返回首页</a>
        </div>
    </footer>
</div>

<script>
function toggleDetailLang(lang) {
    var cn = document.getElementById('detail-cn');
    var en = document.getElementById('detail-en');
    var btnCn = document.getElementById('detail-btn-cn');
    var btnEn = document.getElementById('detail-btn-en');
    if (lang === 'cn') {
        cn.classList.remove('hidden');
        en.classList.add('hidden');
        btnCn.classList.add('active');
        btnEn.classList.remove('active');
    } else {
        en.classList.remove('hidden');
        cn.classList.add('hidden');
        btnEn.classList.add('active');
        btnCn.classList.remove('active');
    }
}
</script>

</body>
</html>
