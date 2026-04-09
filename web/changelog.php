<?php
/**
 * Changelog 主页面
 * 上半部分：5 个最新版本卡片（2+3 布局）
 * 下半部分：5 列历史版本号列表
 */
require_once __DIR__ . '/config.php';

$data = load_changelog_data();
if (!$data) {
    die('无法加载 Changelog 数据，请先运行 python src/generators/changelog_json.py');
}

// 仓库显示顺序
$repo_order = ['Claude Code', 'OpenCode', 'OpenClaw', 'Gemini CLI', 'Codex'];
$repos = $data['repos'] ?? [];
$trends = load_changelog_trend();

// 统计数据
$total_releases = 0;
$repo_with_data = 0;
$latest_date = '';
foreach ($repos as $r) {
    $total_releases += $r['total'] ?? 0;
    if (($r['total'] ?? 0) > 0) $repo_with_data++;
    foreach ($r['releases'] ?? [] as $rel) {
        $d = substr($rel['published_at'] ?? '', 0, 10);
        if ($d > $latest_date) $latest_date = $d;
    }
}
$total_repos = count($repo_order);

// ========== 图表数据计算 ==========
$chart_days = 30; // 最近30天
$today = date('Y-m-d');
$date_range = [];
for ($i = $chart_days - 1; $i >= 0; $i--) {
    $date_range[] = date('Y-m-d', strtotime("-{$i} days"));
}

// 按仓库统计每天发布数量
$daily_counts = [];
$repo_total_30d = [];

foreach ($repo_order as $repo_name) {
    $repo = $repos[$repo_name] ?? null;
    $releases = $repo['releases'] ?? [];
    $repo_total_30d[$repo_name] = 0;

    foreach ($releases as $r) {
        $date = substr($r['published_at'] ?? '', 0, 10);
        if ($date && $date >= $date_range[0] && $date <= $today) {
            if (!isset($daily_counts[$date])) $daily_counts[$date] = [];
            if (!isset($daily_counts[$date][$repo_name])) $daily_counts[$date][$repo_name] = 0;
            $daily_counts[$date][$repo_name]++;
            $repo_total_30d[$repo_name]++;
        }
    }
}

// 构建 Chart.js 数据
$chart_labels = json_encode(array_map(function($d) { return substr($d, 5); }, $date_range)); // MM-DD 格式

// 每个仓库的数据
$chart_datasets = [];
$colors = [
    'Claude Code' => '#FF6B6B',
    'OpenCode' => '#4ECDC4',
    'OpenClaw' => '#45B7D1',
    'Gemini CLI' => '#96CEB4',
    'Codex' => '#FFEAA7'
];
foreach ($repo_order as $repo_name) {
    $data = [];
    foreach ($date_range as $d) {
        $data[] = $daily_counts[$d][$repo_name] ?? 0;
    }
    $chart_datasets[] = json_encode([
        'label' => $repo_name,
        'data' => $data,
        'backgroundColor' => $colors[$repo_name] ?? '#999',
        'borderColor' => $colors[$repo_name] ?? '#999',
        'fill' => false,
        'tension' => 0.3
    ]);
}

$chart_labels_json = $chart_labels;
$chart_datasets_json = implode(',', $chart_datasets);

// ========== 新图表：预发布版本占比 ==========
$prerelease_count = 0;
$stable_count = 0;
$repo_prerelease = []; // 各仓库预发布数量

foreach ($repo_order as $repo_name) {
    $repo = $repos[$repo_name] ?? null;
    $releases = $repo['releases'] ?? [];
    $repo_prerelease[$repo_name] = 0;
    foreach ($releases as $r) {
        if (!empty($r['is_prerelease'])) {
            $prerelease_count++;
            $repo_prerelease[$repo_name]++;
        } else {
            $stable_count++;
        }
    }
}

$prerelease_data = json_encode([
    ['label' => '正式版', 'data' => $stable_count, 'backgroundColor' => '#4ECDC4'],
    ['label' => '预发布版', 'data' => $prerelease_count, 'backgroundColor' => '#FF6B6B']
]);

// 各仓库预发布占比
$prerelease_by_repo = [];
foreach ($repo_order as $repo_name) {
    $repo = $repos[$repo_name] ?? null;
    $releases = $repo['releases'] ?? [];
    $total = count($releases);
    $prerelease = $repo_prerelease[$repo_name];
    $prerelease_by_repo[] = json_encode([
        'label' => $repo_name,
        'data' => $total > 0 ? round($prerelease / $total * 100, 1) : 0,
        'backgroundColor' => $colors[$repo_name] ?? '#999'
    ]);
}
$prerelease_by_repo_json = implode(',', $prerelease_by_repo);

// ========== 新图表：更新内容长度对比 ==========
$repo_body_lengths = [];
foreach ($repo_order as $repo_name) {
    $repo = $repos[$repo_name] ?? null;
    $releases = $repo['releases'] ?? [];
    $total_len = 0;
    $count = 0;
    foreach ($releases as $r) {
        $body = $r['body_cn'] ?? $r['body_en'] ?? '';
        if ($body) {
            $total_len += mb_strlen($body);
            $count++;
        }
    }
    $avg_len = $count > 0 ? round($total_len / $count) : 0;
    $repo_body_lengths[] = json_encode([
        'label' => $repo_name,
        'data' => $avg_len,
        'backgroundColor' => $colors[$repo_name] ?? '#999'
    ]);
}
$body_length_json = implode(',', $repo_body_lengths);
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>大黑AI工具速报</title>
    <link rel="stylesheet" href="css/style.css">
    <link rel="stylesheet" href="css/changelog.css">
    <link rel="alternate" type="application/rss+xml" title="大黑AI工具速报 RSS" href="changelog_rss.php">
</head>
<body>

<div class="changelog-wrapper">
    <!-- 页头 -->
    <section class="changelog-hero">
        <img src="images/avatar-placeholder.svg" alt="大黑" class="changelog-avatar">
        <h1>大黑AI工具速报</h1>
        <p>追踪 AI 编程工具的每一次版本更新</p>
        <div class="changelog-stats">
            <div class="changelog-stat">
                <div class="changelog-stat-number"><?php echo $total_repos; ?></div>
                <div class="changelog-stat-label">追踪项目</div>
            </div>
            <div class="changelog-stat">
                <div class="changelog-stat-number"><?php echo $total_releases; ?></div>
                <div class="changelog-stat-label">收录版本</div>
            </div>
            <div class="changelog-stat">
                <div class="changelog-stat-number"><?php echo $latest_date ? substr($latest_date, 5) : '-'; ?></div>
                <div class="changelog-stat-label">最近更新</div>
            </div>
        </div>
        <div class="changelog-nav">
            <a href="index.php" class="changelog-btn changelog-btn-secondary">AI 热点主页</a>
            <a href="changelog_rss.php" class="changelog-btn changelog-btn-secondary" target="_blank">AI工具RSS订阅</a>
            <a href="https://daheiai.com" class="changelog-btn changelog-btn-secondary" target="_blank">大黑的主页</a>
        </div>
    </section>
    <section class="latest-cards">
        <!-- 第一排：2 个 -->
        <div class="latest-cards-row row-2">
            <?php for ($i = 0; $i < 2; $i++): ?>
                <?php echo render_release_card($repo_order[$i], $repos); ?>
            <?php endfor; ?>
        </div>
        <!-- 第二排：3 个 -->
        <div class="latest-cards-row row-3">
            <?php for ($i = 2; $i < 5; $i++): ?>
                <?php echo render_release_card($repo_order[$i], $repos); ?>
            <?php endfor; ?>
        </div>
    </section>

    <!-- 历史版本号 -->
    <section class="history-section">
        <h2>历史版本</h2>
        <div class="history-columns">
            <?php foreach ($repo_order as $name): ?>
            <?php
                $repo = $repos[$name] ?? null;
                $releases = $repo['releases'] ?? [];
                $total = count($releases);
                // 取近 10 期的 tag_name 用于趋势占位
                $recent_tags = array_slice(array_column($releases, 'tag_name'), 0, 10);
            ?>
            <div class="history-col">
                <div class="history-col-title">
                    <?php echo htmlspecialchars($name); ?>
                    <span class="history-col-count">(<?php echo $total; ?>)</span>
                </div>
                <!-- 版本号列表（固定高度可滚动） -->
                <ul class="version-list">
                    <?php foreach ($releases as $r): ?>
                    <li>
                        <a href="changelog_detail.php?id=<?php echo urlencode($r['id']); ?>"
                           class="<?php echo !empty($r['is_prerelease']) ? 'prerelease' : ''; ?>"
                           title="<?php echo htmlspecialchars($r['published_at']); ?>">
                            <?php echo htmlspecialchars($r['tag_name']); ?>
                        </a>
                    </li>
                    <?php endforeach; ?>
                    <?php if ($total === 0): ?>
                    <li style="color: var(--sub-text); font-size: 0.8rem;">暂无数据</li>
                    <?php endif; ?>
                </ul>
            </div>
            <?php endforeach; ?>
        </div>
    </section>

    <!-- 图表区域 -->
    <section class="chart-section">
        <h2>数据分析</h2>

        <!-- 第一排：2个 -->
        <div class="chart-row row-2">
            <div class="chart-container">
                <h3>各仓库发布数量 <span class="chart-hint">（近30天）</span></h3>
                <canvas id="barChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>版本类型分布 <span class="chart-hint">（全部）</span></h3>
                <canvas id="pieChart"></canvas>
            </div>
        </div>

        <!-- 第二排：3个 -->
        <div class="chart-row row-3">
            <div class="chart-container">
                <h3>每日发布趋势 <span class="chart-hint">（近30天）</span></h3>
                <canvas id="lineChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>各仓库预发布占比 <span class="chart-hint">（全部）</span></h3>
                <canvas id="prereleaseBarChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>平均更新内容长度 <span class="chart-hint">（字符数）</span></h3>
                <canvas id="lengthChart"></canvas>
            </div>
        </div>
    </section>

    <!-- 更新趋势 -->
    <section class="trend-section">
        <h2>近期更新趋势</h2>
        <?php foreach ($repo_order as $name): ?>
        <?php
            $repo = $repos[$name] ?? null;
            $releases = $repo['releases'] ?? [];
            $recent10 = array_slice($releases, 0, 10);
        ?>
        <div class="trend-row">
            <div class="trend-row-header">
                <span class="trend-row-name"><?php echo htmlspecialchars($name); ?></span>
                <?php if (!empty($recent10)): ?>
                <span class="trend-row-range"><?php echo htmlspecialchars($recent10[count($recent10)-1]['tag_name']); ?> → <?php echo htmlspecialchars($recent10[0]['tag_name']); ?></span>
                <?php endif; ?>
            </div>
            <div class="trend-row-content">
                <?php
                    $trend_text = $trends[$name] ?? '';
                ?>
                <?php if (empty($recent10)): ?>
                    <span class="trend-row-empty">暂无数据</span>
                <?php elseif ($trend_text): ?>
                    <?php echo htmlspecialchars($trend_text); ?>
                <?php else: ?>
                    <span class="trend-row-placeholder">趋势分析即将上线</span>
                <?php endif; ?>
            </div>
        </div>
        <?php endforeach; ?>
    </section>

    <!-- 页脚 -->
    <footer class="changelog-footer">
        <div>
            <a href="index.php">返回首页</a>
            <a href="realtime.php">最新速报</a>
        </div>
    </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
// 图表数据
const chartLabels = <?php echo $chart_labels_json; ?>;
const chartDatasets = [<?php echo $chart_datasets_json; ?>];
const repoOrder = <?php echo json_encode($repo_order); ?>;

// 柱状图：各仓库发布数量
new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
        labels: chartLabels,
        datasets: chartDatasets.map(ds => ({
            ...ds,
            backgroundColor: ds.borderColor,
            borderWidth: 1
        }))
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { position: 'bottom' }
        },
        scales: {
            y: { beginAtZero: true, ticks: { stepSize: 1 } }
        }
    }
});

// 饼图：版本类型分布
new Chart(document.getElementById('pieChart'), {
    type: 'pie',
    data: {
        labels: ['正式版', '预发布版'],
        datasets: [{
            data: [<?php echo $stable_count; ?>, <?php echo $prerelease_count; ?>],
            backgroundColor: ['#4ECDC4', '#FF6B6B']
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { position: 'bottom' }
        }
    }
});

// 折线图：每日发布趋势
new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: {
        labels: chartLabels,
        datasets: chartDatasets
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { position: 'bottom' }
        },
        scales: {
            y: { beginAtZero: true, ticks: { stepSize: 1 } }
        },
        interaction: {
            mode: 'index',
            intersect: false
        }
    }
});

// 柱状图：各仓库预发布占比
new Chart(document.getElementById('prereleaseBarChart'), {
    type: 'bar',
    data: {
        labels: repoOrder,
        datasets: [{
            label: '预发布占比(%)',
            data: [<?php
                $lengths = [];
                foreach ($repo_order as $repo_name) {
                    $repo = $repos[$repo_name] ?? null;
                    $releases = $repo['releases'] ?? [];
                    $total = count($releases);
                    $prerelease = 0;
                    foreach ($releases as $rel) { if (!empty($rel['is_prerelease'])) $prerelease++; }
                    $lengths[] = $total > 0 ? round($prerelease / $total * 100, 1) : 0;
                }
                echo implode(',', $lengths);
            ?>],
            backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        indexAxis: 'y',
        plugins: {
            legend: { display: false }
        },
        scales: {
            x: { beginAtZero: true, max: 100 }
        }
    }
});

// 柱状图：平均更新内容长度
new Chart(document.getElementById('lengthChart'), {
    type: 'bar',
    data: {
        labels: repoOrder,
        datasets: [{
            label: '平均字符数',
            data: [<?php
                $lengths = [];
                foreach ($repo_order as $repo_name) {
                    $repo = $repos[$repo_name] ?? null;
                    $releases = $repo['releases'] ?? [];
                    $total_len = 0;
                    $count = 0;
                    foreach ($releases as $r) {
                        $body = $r['body_cn'] ?? $r['body_en'] ?? '';
                        if ($body) {
                            $total_len += mb_strlen($body);
                            $count++;
                        }
                    }
                    $lengths[] = $count > 0 ? round($total_len / $count) : 0;
                }
                echo implode(',', $lengths);
            ?>],
            backgroundColor: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: { display: false }
        },
        scales: {
            y: { beginAtZero: true }
        }
    }
});
</script>

<script>
// 每个卡片当前显示的版本索引和语言
var cardState = {};

function getState(cardId) {
    if (!cardState[cardId]) cardState[cardId] = { idx: 0, lang: 'cn' };
    return cardState[cardId];
}

function toggleLang(cardId, lang) {
    var state = getState(cardId);
    state.lang = lang;
    showVersion(cardId, state.idx, lang);
    // 更新按钮
    document.getElementById(cardId + '-btn-cn').classList.toggle('active', lang === 'cn');
    document.getElementById(cardId + '-btn-en').classList.toggle('active', lang === 'en');
}

function switchVersion(cardId, idx, total) {
    var state = getState(cardId);
    state.idx = idx;
    showVersion(cardId, idx, state.lang);
    // 更新版本号和日期
    var metaEl = document.getElementById(cardId + '-meta');
    if (metaEl) {
        var meta = JSON.parse(metaEl.textContent);
        document.getElementById(cardId + '-tag').textContent = meta[idx].tag;
        document.getElementById(cardId + '-date').textContent = meta[idx].date;
        document.getElementById(cardId + '-detail').href = 'changelog_detail.php?id=' + encodeURIComponent(meta[idx].id);
    }
    // 更新圆点 — 遍历同一行内所有圆点
    var clickedBtn = event.currentTarget;
    var nav = clickedBtn.parentNode;
    nav.querySelectorAll('.version-dot').forEach(function(dot, i) {
        dot.classList.toggle('active', i === idx);
    });
}

function showVersion(cardId, idx, lang) {
    // 先隐藏所有
    var body = document.getElementById(cardId + '-tag').closest('.release-card').querySelector('.card-body');
    body.querySelectorAll('.card-body-content').forEach(function(el) { el.classList.add('hidden'); });
    // 显示当前版本的对应语言
    var target = document.getElementById(cardId + '-' + idx + '-' + lang);
    if (target) target.classList.remove('hidden');
}
</script>

</body>
</html>

<?php
/**
 * 渲染单个 release 卡片（支持切换最近 5 期）
 */
function render_release_card($name, $repos) {
    $repo = $repos[$name] ?? null;
    $releases = $repo['releases'] ?? [];
    $top5 = array_slice($releases, 0, 5);
    $card_id = 'card-' . preg_replace('/[^a-z0-9]/', '', strtolower($name));

    ob_start();
    if (!empty($top5)): ?>
    <div class="release-card">
        <div class="card-top">
            <span class="card-repo-name"><?php echo htmlspecialchars($name); ?></span>
            <span class="card-tag" id="<?php echo $card_id; ?>-tag"><?php echo htmlspecialchars($top5[0]['tag_name']); ?></span>
        </div>
        <div class="card-date" id="<?php echo $card_id; ?>-date"><?php echo htmlspecialchars(substr($top5[0]['published_at'], 0, 10)); ?></div>
        <div class="lang-toggle">
            <button class="lang-btn active" id="<?php echo $card_id; ?>-btn-cn" onclick="toggleLang('<?php echo $card_id; ?>','cn')">中文</button>
            <button class="lang-btn" id="<?php echo $card_id; ?>-btn-en" onclick="toggleLang('<?php echo $card_id; ?>','en')">EN</button>
        </div>
        <div class="card-body">
            <?php foreach ($top5 as $idx => $r): ?>
            <div class="card-body-content <?php echo $idx > 0 ? 'hidden' : ''; ?>" id="<?php echo $card_id; ?>-<?php echo $idx; ?>-cn"><?php echo htmlspecialchars($r['body_cn'] ?: $r['body_en']); ?></div>
            <div class="card-body-content hidden" id="<?php echo $card_id; ?>-<?php echo $idx; ?>-en"><?php echo htmlspecialchars($r['body_en']); ?></div>
            <?php endforeach; ?>
        </div>
        <div class="card-footer">
            <a href="changelog_detail.php?id=<?php echo urlencode($top5[0]['id']); ?>" class="card-footer-link" id="<?php echo $card_id; ?>-detail">查看详情 →</a>
            <?php if (count($top5) > 1): ?>
            <div class="card-version-nav">
                <?php foreach ($top5 as $idx => $r): ?>
                <button class="version-dot <?php echo $idx === 0 ? 'active' : ''; ?>"
                        onclick="switchVersion('<?php echo $card_id; ?>', <?php echo $idx; ?>, <?php echo count($top5); ?>)"
                        title="<?php echo htmlspecialchars($r['tag_name']); ?>">
                    <?php echo $idx + 1; ?>
                </button>
                <?php endforeach; ?>
            </div>
            <?php endif; ?>
        </div>
        <!-- 隐藏的元数据供 JS 使用 -->
        <script type="application/json" id="<?php echo $card_id; ?>-meta"><?php echo json_encode(array_map(function($r) {
            return ['tag' => $r['tag_name'], 'date' => substr($r['published_at'], 0, 10), 'id' => $r['id']];
        }, $top5), JSON_UNESCAPED_UNICODE); ?></script>
    </div>
    <?php else: ?>
    <div class="release-card release-card-empty">
        <div class="card-top">
            <span class="card-repo-name"><?php echo htmlspecialchars($name); ?></span>
        </div>
        <p class="card-empty-text">暂无版本数据</p>
    </div>
    <?php endif;
    return ob_get_clean();
}
