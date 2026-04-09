<?php
/**
 * 历史期刊列表
 */

require_once __DIR__ . '/config.php';

$history = get_history_list();
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>历史期刊 - 大黑AI速报</title>
    <link rel="stylesheet" href="css/style.css">
    <link rel="alternate" type="application/rss+xml" title="大黑AI速报 RSS" href="rss.php">
    <style>
        .history-wrapper {
            width: 390px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            background: var(--bg-color);
            box-shadow: 0 0 20px rgba(0,0,0,0.05);
        }
        .history-header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }
        .history-header h1 {
            font-family: "Noto Serif SC", "Songti SC", serif;
            font-size: 1.2rem;
            color: var(--text-color);
            font-weight: 900;
            margin: 0;
        }
        .history-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .history-item {
            border-bottom: 1px solid var(--border-color);
        }
        .history-item a {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 12px;
            color: var(--text-color);
            text-decoration: none;
            transition: background 0.2s;
        }
        .history-item a:hover {
            background: var(--banner-bg);
        }
        .history-date {
            font-size: 0.95rem;
        }
        .history-issue {
            font-size: 0.85rem;
            color: var(--sub-text);
        }
        .history-back {
            text-align: center;
            padding: 30px 0;
        }
        .history-back a {
            color: var(--sub-text);
            text-decoration: none;
            font-size: 0.85rem;
        }
        .history-back a:hover {
            color: var(--accent-color);
        }
        .history-empty {
            text-align: center;
            color: var(--sub-text);
            padding: 60px 20px;
        }
    </style>
</head>
<body>

    <div class="history-wrapper">
        <header class="history-header">
            <h1>历史期刊</h1>
        </header>

        <?php if (empty($history)): ?>
        <div class="history-empty">
            暂无历史记录
        </div>
        <?php else: ?>
        <ul class="history-list">
            <?php foreach ($history as $item): ?>
            <li class="history-item">
                <a href="realtime.php?file=<?php echo htmlspecialchars($item['filename']); ?>">
                    <span class="history-date"><?php echo htmlspecialchars($item['date']); ?> <?php echo htmlspecialchars($item['time']); ?></span>
                    <span class="history-issue">第<?php echo htmlspecialchars($item['issue_number']); ?>期</span>
                </a>
            </li>
            <?php endforeach; ?>
        </ul>
        <?php endif; ?>

        <div class="history-back">
            <a href="realtime.php">返回最新</a>
            <span style="margin: 0 8px; color: var(--sub-text);">·</span>
            <a href="rss.php" target="_blank">RSS 订阅</a>
        </div>
    </div>

<script> var _mtj = _mtj || []; (function () { var mtj = document.createElement("script"); mtj.src = "https://node96.aizhantj.com:21233/tjjs/?k=qk25ajlrkia"; var s = document.getElementsByTagName("script")[0]; s.parentNode.insertBefore(mtj, s); })(); </script>
</body>
</html>
