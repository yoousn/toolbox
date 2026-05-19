// ============================================================
// 工具箱配置 —— 单一数据源
// ============================================================
// 新增工具时,只需在对应分类的 tools 数组里加一项。
// 同时记得在 main.py 注册 backend、在 backends/ 写后端、在 qml/pages/ 写页面。
// ------------------------------------------------------------
// 字段说明:
//   id      : 唯一标识(英文,kebab-case),仅用于调试
//   name    : 侧边栏显示名
//   icon    : emoji 图标(可选,留空就只显示文字)
//   page    : 对应的 QML 页面路径(相对于 qml/ 目录)
//   tags    : 关键词,以后做搜索时用(可选)
// ============================================================

.pragma library

var categories = [
    {
        id: "work",
        name: "工作",
        icon: "💼",
        tools: [
            {
                id: "product-matrix",
                name: "商品矩阵 (尺码表)",
                icon: "📐",
                page: "pages/ProductMatrixPage.qml",
                tags: ["尺码", "矩阵", "Excel"]
            },
            {
                id: "image-distributor",
                name: "尺码表批量分发",
                icon: "📤",
                page: "pages/ImageDistributorPage.qml",
                tags: ["图片", "分发"]
            },
            {
                id: "video-processor",
                name: "视频批量处理",
                icon: "🎬",
                page: "pages/VideoProcessorPage.qml",
                tags: ["视频", "批量"]
            },
            {
                id: "image-file-checker",
                name: "图片批量删除",
                icon: "🗑️",
                page: "pages/ImageFileCheckerPage.qml",
                tags: ["图片", "清理"]
            },
            {
                id: "attendance-sync",
                name: "KQ",
                icon: "📅",
                page: "pages/AttendanceSyncPage.qml",
                tags: ["考勤", "同步"]
            },
            {
                id: "cert-generator",
                name: "批量生成合格证",
                icon: "🏷️",
                page: "pages/CertGeneratorPage.qml",
                tags: ["合格证", "批量"]
            },
            {
                id: "white-bg-processor",
                name: "智能白底图生图",
                icon: "🖼️",
                page: "pages/WhiteBgProcessorPage.qml",
                tags: ["AI", "去背景", "白底图"]
            }
        ]
    },
    {
        id: "daily",
        name: "日常",
        icon: "🏠",
        tools: [
            // 以后日常类的小工具放这里
            // 例如:文件改名、二维码生成、剪贴板增强 ...
        ]
    },
    {
        id: "misc",
        name: "其他",
        icon: "🧰",
        tools: [
            // 暂时归类不明的工具放这里
        ]
    }
]

// 把所有工具拍平成一个数组,主内容区按这个顺序渲染页面
function flatTools() {
    var list = []
    for (var i = 0; i < categories.length; i++) {
        var cat = categories[i]
        for (var j = 0; j < cat.tools.length; j++) {
            list.push(cat.tools[j])
        }
    }
    return list
}
