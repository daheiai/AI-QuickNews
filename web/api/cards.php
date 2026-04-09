<?php
/**
 * 卡片数据 API
 * 用于无限滚动加载
 *
 * 参数:
 *   offset: 起始位置（默认 0）
 *   limit: 返回数量（默认 20，最大 50）
 */

require_once dirname(__DIR__) . '/config.php';

header('Content-Type: application/json; charset=UTF-8');

// 获取参数
$offset = max(0, intval($_GET['offset'] ?? 0));
$limit = min(50, max(1, intval($_GET['limit'] ?? 20)));

// 获取历史列表
$history = get_history_list();
$total = count($history);

// 切片
$items = array_slice($history, $offset, $limit);

// 构建卡片数据
$cards = [];
foreach ($items as $item) {
    $data = load_quick_data($item['filename'] . '.json');
    if (!$data) continue;

    // 收集本期品牌
    $brands = [];
    $brand_logos = [];
    foreach ($data['items'] ?? [] as $news_item) {
        if (!empty($news_item['brands'])) {
            foreach ($news_item['brands'] as $brand) {
                if (!in_array($brand, $brands) && count($brands) < 5) {
                    $brands[] = $brand;
                    $logo = get_brand_logo($brand);
                    if ($logo) {
                        $brand_logos[] = [
                            'brand' => $brand,
                            'logo' => $logo
                        ];
                    }
                }
            }
        }
    }

    $cards[] = [
        'filename' => $item['filename'],
        'date' => $item['date'],
        'time' => $item['time'],
        'issue_number' => $data['issue_number'] ?? '?',
        'summary' => str_replace(['【', '】'], ['', ''], $data['summary'] ?? ''),
        'item_count' => count($data['items'] ?? []),
        'brand_logos' => $brand_logos,
    ];
}

// 返回结果
echo json_encode([
    'success' => true,
    'data' => $cards,
    'meta' => [
        'offset' => $offset,
        'limit' => $limit,
        'total' => $total,
        'has_more' => ($offset + $limit) < $total
    ]
], JSON_UNESCAPED_UNICODE);
