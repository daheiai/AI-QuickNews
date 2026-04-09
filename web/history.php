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
    <style>
        .history-wrapper {
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            background: #0f0f0f;
        }
        .history-header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #222;
            margin-bottom: 20px;
        }
        .history-header h1 {
            font-size: 1.2rem;
            color: #999;
            font-weight: normal;
            margin: 0;
        }
        .history-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .history-item {
            border-bottom: 1px solid #1a1a1a;
        }
        .history-item a {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 12px;
            color: #ccc;
            text-decoration: none;
            transition: background 0.2s;
        }
        .history-item a:hover {
            background: #1a1a1a;
        }
        .history-date {
            font-size: 0.95rem;
        }
        .history-issue {
            font-size: 0.85rem;
            color: #666;
        }
        .history-back {
            text-align: center;
            padding: 30px 0;
        }
        .history-back a {
            color: #666;
            text-decoration: none;
            font-size: 0.85rem;
        }
        .history-back a:hover {
            color: #999;
        }
        .history-empty {
            text-align: center;
            color: #666;
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
                <a href="index.php?file=<?php echo htmlspecialchars($item['filename']); ?>">
                    <span class="history-date"><?php echo htmlspecialchars($item['date']); ?> <?php echo htmlspecialchars($item['time']); ?></span>
                    <span class="history-issue">第<?php echo htmlspecialchars($item['issue_number']); ?>期</span>
                </a>
            </li>
            <?php endforeach; ?>
        </ul>
        <?php endif; ?>

        <div class="history-back">
            <a href="index.php">返回最新</a>
        </div>
    </div>

</body>
</html>
