<?php
/**
 * AI 快讯网页配置文件
 */

// 项目根目录（相对于 web 目录）
define('PROJECT_ROOT', dirname(__DIR__));

// 数据目录
define('DATA_DIR', PROJECT_ROOT . '/data');
define('WEB_JSON_DIR', DATA_DIR . '/web-json');

// JSON 数据文件路径
define('QUICK_LATEST_JSON', WEB_JSON_DIR . '/quick_latest.json');

// Logo 配置
define('LOGO_DIR', __DIR__ . '/images/logos');

// 品牌 Logo 映射（品牌 key => logo 文件名）
// 根据 images/logos/ 目录下的文件自动生成
$BRAND_LOGOS = [
    // 主流大模型
    'openai' => 'openai.png',
    'claude' => 'claude.png',
    'anthropic' => 'claude.png',
    'deepseek' => 'deepseek.png',
    'qwen' => 'qwen.png',
    'gemini' => 'gemini.png',
    'gemma' => 'gemma.png',
    'meta' => 'meta.png',
    'metaai' => 'metaai.png',
    'mistral' => 'mistral.png',
    'cohere' => 'cohere.png',
    'xai' => 'xai.png',
    'grok' => 'grok.png',

    // 国内大模型
    'kimi' => 'kimi.png',
    'moonshot' => 'moonshot.png',
    'minimax' => 'minimax.png',
    'hailuo' => 'hailuo.png',
    'zhipu' => 'zhipu.png',
    'chatglm' => 'chatglm.png',
    'baidu' => 'baidu.png',
    'wenxin' => 'wenxin.png',
    'doubao' => 'doubao.png',
    'bytedance' => 'bytedance.png',
    'alibaba' => 'alibaba.png',
    'hunyuan' => 'hunyuan.png',
    'spark' => 'spark.png',
    'tiangong' => 'tiangong.png',
    'qingyan' => 'qingyan.png',

    // 图像/视频生成
    'stability' => 'stability.png',
    'midjourney' => 'midjourney.png',
    'runway' => 'runway.png',
    'pika' => 'pika.png',
    'flux' => 'flux.png',
    'ideogram' => 'ideogram.png',
    'pixverse' => 'pixverse.png',
    'haiper' => 'haiper.png',
    'viggle' => 'viggle.png',
    'civitai' => 'civitai.png',
    'novelai' => 'novelai.png',
    'clipdrop' => 'clipdrop.png',

    // 音频生成
    'suno' => 'suno.png',
    'udio' => 'udio.png',

    // 开发工具
    'github' => 'github.png',
    'githubcopilot' => 'githubcopilot.png',
    'copilot' => 'copilot.png',
    'cursor' => 'cursor.png',
    'windsurf' => 'windsurf.png',
    'cline' => 'cline.png',
    'manus' => 'manus.png',

    // 平台/工具
    'huggingface' => 'huggingface.png',
    'ollama' => 'ollama.png',
    'gradio' => 'gradio.png',
    'langchain' => 'langchain.png',
    'comfyui' => 'comfyui.png',
    'openwebui' => 'openwebui.png',
    'lmstudio' => 'lmstudio.png',
    'vllm' => 'vllm.png',
    'xinference' => 'xinference.png',
    'modelscope' => 'modelscope.png',
    'dify' => 'dify.png',
    'coze' => 'coze.png',
    'n8n' => 'n8n.png',
    'notion' => 'notion.png',
    'notebooklm' => 'notebooklm.png',
    'mcp' => 'mcp.png',

    // 云服务/API
    'azure' => 'azure.png',
    'google' => 'google.png',
    'googlecloud' => 'googlecloud.png',
    'nvidia' => 'nvidia.png',
    'microsoft' => 'microsoft.png',
    'apple' => 'apple.png',
    'ibm' => 'ibm.png',
    'cloudflare' => 'cloudflare.png',
    'snowflake' => 'snowflake.png',
    'huawei' => 'huawei.png',
    'huaweicloud' => 'huaweicloud.png',
    'baiducloud' => 'baiducloud.png',
    'qiniu' => 'qiniu.png',

    // API 聚合/推理平台
    'openrouter' => 'openrouter.png',
    'deepinfra' => 'deepinfra.png',
    'fireworks' => 'fireworks.png',
    'leptonai' => 'leptonai.png',
    'hyperbolic' => 'hyperbolic.png',
    'cerebras' => 'cerebras.png',
    'siliconcloud' => 'siliconcloud.png',
    'aihubmix' => 'aihubmix.png',
    'bailian' => 'bailian.png',
    'giteeai' => 'giteeai.png',

    // 其他
    'bilibili' => 'bilibili.png',
    'monica' => 'monica.png',
    'flowith' => 'flowith.png',
    'youmind' => 'youmind.png',
    'flora' => 'flora.png',
    'dolphin' => 'dolphin.png',
    'goose' => 'goose.png',
    'baseten' => 'baseten.png',
    'friendli' => 'friendli.png',
    'inference' => 'inference.png',
    'jina' => 'jina.png',
    'railway' => 'railway.png',
    'relace' => 'relace.png',
    'skywork' => 'skywork.png',
    'smithery' => 'smithery.png',
    'statecloud' => 'statecloud.png',
    'sync' => 'sync.png',
    'tavily' => 'tavily.png',
    'yandex' => 'yandex.png',
    'nousresearch' => 'nousresearch.png',
    'aistudio' => 'aistudio.png',
    'baai' => 'baai.png',
    'newapi' => 'newapi.png',
];

// 品牌颜色映射（用于标签背景色）
$BRAND_COLORS = [
    // 主流大模型
    'openai' => ['bg' => 'rgba(16, 163, 127, 0.2)', 'text' => '#10a37f'],
    'claude' => ['bg' => 'rgba(212, 165, 116, 0.2)', 'text' => '#d4a574'],
    'anthropic' => ['bg' => 'rgba(212, 165, 116, 0.2)', 'text' => '#d4a574'],
    'deepseek' => ['bg' => 'rgba(79, 70, 229, 0.2)', 'text' => '#4f46e5'],
    'gemini' => ['bg' => 'rgba(66, 133, 244, 0.2)', 'text' => '#4285f4'],
    'gemma' => ['bg' => 'rgba(66, 133, 244, 0.2)', 'text' => '#4285f4'],
    'meta' => ['bg' => 'rgba(6, 104, 225, 0.2)', 'text' => '#0668e1'],
    'metaai' => ['bg' => 'rgba(6, 104, 225, 0.2)', 'text' => '#0668e1'],
    'mistral' => ['bg' => 'rgba(255, 140, 0, 0.2)', 'text' => '#ff8c00'],
    'cohere' => ['bg' => 'rgba(212, 78, 156, 0.2)', 'text' => '#d44e9c'],
    'xai' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'grok' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],

    // 国内大模型
    'qwen' => ['bg' => 'rgba(22, 119, 255, 0.2)', 'text' => '#1677ff'],
    'alibaba' => ['bg' => 'rgba(255, 106, 0, 0.2)', 'text' => '#ff6a00'],
    'kimi' => ['bg' => 'rgba(255, 107, 107, 0.2)', 'text' => '#ff6b6b'],
    'moonshot' => ['bg' => 'rgba(255, 107, 107, 0.2)', 'text' => '#ff6b6b'],
    'minimax' => ['bg' => 'rgba(245, 158, 11, 0.2)', 'text' => '#f59e0b'],
    'hailuo' => ['bg' => 'rgba(245, 158, 11, 0.2)', 'text' => '#f59e0b'],
    'zhipu' => ['bg' => 'rgba(102, 126, 234, 0.2)', 'text' => '#667eea'],
    'chatglm' => ['bg' => 'rgba(102, 126, 234, 0.2)', 'text' => '#667eea'],
    'baidu' => ['bg' => 'rgba(45, 140, 255, 0.2)', 'text' => '#2d8cff'],
    'wenxin' => ['bg' => 'rgba(45, 140, 255, 0.2)', 'text' => '#2d8cff'],
    'doubao' => ['bg' => 'rgba(0, 206, 201, 0.2)', 'text' => '#00cec9'],
    'bytedance' => ['bg' => 'rgba(0, 206, 201, 0.2)', 'text' => '#00cec9'],
    'hunyuan' => ['bg' => 'rgba(7, 193, 96, 0.2)', 'text' => '#07c160'],
    'spark' => ['bg' => 'rgba(0, 150, 255, 0.2)', 'text' => '#0096ff'],
    'tiangong' => ['bg' => 'rgba(147, 112, 219, 0.2)', 'text' => '#9370db'],

    // 图像/视频生成
    'stability' => ['bg' => 'rgba(168, 85, 247, 0.2)', 'text' => '#a855f7'],
    'midjourney' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'runway' => ['bg' => 'rgba(139, 92, 246, 0.2)', 'text' => '#8b5cf6'],
    'pika' => ['bg' => 'rgba(236, 72, 153, 0.2)', 'text' => '#ec4899'],
    'flux' => ['bg' => 'rgba(34, 197, 94, 0.2)', 'text' => '#22c55e'],
    'ideogram' => ['bg' => 'rgba(99, 102, 241, 0.2)', 'text' => '#6366f1'],
    'suno' => ['bg' => 'rgba(251, 191, 36, 0.2)', 'text' => '#fbbf24'],
    'udio' => ['bg' => 'rgba(168, 85, 247, 0.2)', 'text' => '#a855f7'],

    // 开发工具
    'github' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'copilot' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'cursor' => ['bg' => 'rgba(0, 122, 255, 0.2)', 'text' => '#007aff'],
    'windsurf' => ['bg' => 'rgba(14, 165, 233, 0.2)', 'text' => '#0ea5e9'],
    'cline' => ['bg' => 'rgba(59, 130, 246, 0.2)', 'text' => '#3b82f6'],
    'manus' => ['bg' => 'rgba(168, 85, 247, 0.2)', 'text' => '#a855f7'],

    // 平台/工具
    'huggingface' => ['bg' => 'rgba(255, 213, 0, 0.2)', 'text' => '#ffd500'],
    'ollama' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'gradio' => ['bg' => 'rgba(255, 140, 0, 0.2)', 'text' => '#ff8c00'],
    'langchain' => ['bg' => 'rgba(29, 78, 216, 0.2)', 'text' => '#1d4ed8'],
    'dify' => ['bg' => 'rgba(79, 70, 229, 0.2)', 'text' => '#4f46e5'],
    'coze' => ['bg' => 'rgba(59, 130, 246, 0.2)', 'text' => '#3b82f6'],
    'notion' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'notebooklm' => ['bg' => 'rgba(66, 133, 244, 0.2)', 'text' => '#4285f4'],

    // 云服务/硬件
    'google' => ['bg' => 'rgba(66, 133, 244, 0.2)', 'text' => '#4285f4'],
    'nvidia' => ['bg' => 'rgba(118, 185, 0, 0.2)', 'text' => '#76b900'],
    'microsoft' => ['bg' => 'rgba(0, 120, 212, 0.2)', 'text' => '#0078d4'],
    'apple' => ['bg' => 'rgba(255, 255, 255, 0.15)', 'text' => '#ffffff'],
    'azure' => ['bg' => 'rgba(0, 120, 212, 0.2)', 'text' => '#0078d4'],
    'cloudflare' => ['bg' => 'rgba(245, 158, 11, 0.2)', 'text' => '#f59e0b'],
    'huawei' => ['bg' => 'rgba(207, 0, 15, 0.2)', 'text' => '#cf000f'],

    // API 聚合平台
    'openrouter' => ['bg' => 'rgba(168, 85, 247, 0.2)', 'text' => '#a855f7'],
    'deepinfra' => ['bg' => 'rgba(59, 130, 246, 0.2)', 'text' => '#3b82f6'],
    'fireworks' => ['bg' => 'rgba(251, 146, 60, 0.2)', 'text' => '#fb923c'],
    'cerebras' => ['bg' => 'rgba(239, 68, 68, 0.2)', 'text' => '#ef4444'],
    'siliconcloud' => ['bg' => 'rgba(79, 70, 229, 0.2)', 'text' => '#4f46e5'],

    // 其他
    'bilibili' => ['bg' => 'rgba(251, 114, 153, 0.2)', 'text' => '#fb7299'],
    'monica' => ['bg' => 'rgba(168, 85, 247, 0.2)', 'text' => '#a855f7'],
    'youmind' => ['bg' => 'rgba(34, 197, 94, 0.2)', 'text' => '#22c55e'],
    'jina' => ['bg' => 'rgba(255, 140, 0, 0.2)', 'text' => '#ff8c00'],
    'tavily' => ['bg' => 'rgba(79, 70, 229, 0.2)', 'text' => '#4f46e5'],
];

// 分类配置
$CATEGORIES = [
    'model' => [
        'name' => '模型动态',
        'icon' => 'cpu',
        'color' => '#a855f7'
    ],
    'product' => [
        'name' => '产品工具',
        'icon' => 'tool',
        'color' => '#3b82f6'
    ],
    'tutorial' => [
        'name' => '技巧教程',
        'icon' => 'book',
        'color' => '#22c55e'
    ],
    'hardware' => [
        'name' => '硬件动态',
        'icon' => 'chip',
        'color' => '#f59e0b'
    ],
    'industry' => [
        'name' => '行业资讯',
        'icon' => 'news',
        'color' => '#6b7280'
    ],
];

/**
 * 加载快讯 JSON 数据
 * @param string|null $filename 指定文件名，null 则加载 latest
 */
function load_quick_data($filename = null) {
    if ($filename) {
        $path = WEB_JSON_DIR . '/' . $filename;
    } else {
        $path = QUICK_LATEST_JSON;
    }

    if (!file_exists($path)) {
        return null;
    }

    $content = file_get_contents($path);
    return json_decode($content, true);
}

/**
 * 获取所有历史快讯文件列表
 * @return array 按时间倒序排列的文件信息
 */
function get_history_list() {
    $files = glob(WEB_JSON_DIR . '/quick_????-??-??_????.json');
    $history = [];

    foreach ($files as $file) {
        $filename = basename($file);
        // 解析文件名: quick_2025-01-30_1430.json
        if (preg_match('/^quick_(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.json$/', $filename, $matches)) {
            $date = $matches[1];
            $hour = $matches[2];
            $minute = $matches[3];

            // 读取文件获取期号
            $content = file_get_contents($file);
            $data = json_decode($content, true);
            $issue_number = $data['issue_number'] ?? '?';

            $history[] = [
                'filename' => str_replace('.json', '', $filename),
                'date' => $date,
                'time' => $hour . ':' . $minute,
                'issue_number' => $issue_number,
                'sort_key' => $date . '_' . $hour . $minute
            ];
        }
    }

    // 按时间倒序排列
    usort($history, function($a, $b) {
        return strcmp($b['sort_key'], $a['sort_key']);
    });

    return $history;
}

/**
 * 获取品牌 Logo URL
 */
function get_brand_logo($brand) {
    global $BRAND_LOGOS;

    $brand = strtolower($brand);
    if (isset($BRAND_LOGOS[$brand])) {
        $logo_file = LOGO_DIR . '/' . $BRAND_LOGOS[$brand];
        if (file_exists($logo_file)) {
            return 'images/logos/' . $BRAND_LOGOS[$brand];
        }
    }
    return null;
}

/**
 * 获取品牌颜色
 */
function get_brand_color($brand) {
    global $BRAND_COLORS;

    $brand = strtolower($brand);
    if (isset($BRAND_COLORS[$brand])) {
        return $BRAND_COLORS[$brand];
    }
    // 默认颜色
    return ['bg' => 'rgba(255, 255, 255, 0.1)', 'text' => '#9ca3af'];
}

/**
 * 获取分类信息
 */
function get_category_info($category) {
    global $CATEGORIES;

    if (isset($CATEGORIES[$category])) {
        return $CATEGORIES[$category];
    }
    return $CATEGORIES['industry'];
}
