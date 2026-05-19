# 办公整合工具箱

> 一个基于 PySide6 + QML 的桌面工具集合,把日常重复劳动一键化。
> 单一仓库、单一可执行文件、自动更新。新工具按"加一项配置"的成本接入。

---

## 目录

- [项目定位](#项目定位)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [架构总览](#架构总览)
- [分类体系](#分类体系)
- [新增一个工具的标准流程](#新增一个工具的标准流程)
- [代码风格与约定](#代码风格与约定)
- [打包与发布](#打包与发布)
- [给 AI 协作者的说明](#给-ai-协作者的说明)

---

## 项目定位

- **单仓库聚合**:所有桌面端小工具放在这一个项目里,共用一套 UI 框架、依赖和发布流程。不为每个小工具单独建仓库。
- **配置驱动**:工具列表与分类全部维护在 `qml/tools_config.js` 一个文件,不在多个 QML 里硬编码字符串。
- **后端纯逻辑、前端纯展示**:`backends/*.py` 不依赖 QML,`qml/pages/*.qml` 不写业务计算。两边通过 `Signal/Slot` 和 `Property` 通信。

---

## 技术栈

| 层级       | 技术                              |
|------------|-----------------------------------|
| 界面       | Qt Quick / QML(Basic 样式)      |
| 应用框架   | PySide6                           |
| 图像处理   | Pillow、onnxruntime(u2net 抠图) |
| 表格处理   | openpyxl                          |
| 视频处理   | (按工具按需引入,如 ffmpeg / opencv) |
| 打包       | PyInstaller                       |
| CI / 发布  | GitHub Actions + Releases         |

---

## 目录结构

```
工作工具箱/
├── main.py                       入口:创建后端实例并注册到 QML
├── backends/                     后端逻辑(纯 Python,无 UI 依赖)
│   ├── __init__.py
│   ├── product_matrix.py
│   ├── image_distributor.py
│   ├── video_processor.py
│   ├── image_file_checker.py
│   ├── attendance_sync.py
│   ├── cert_generator.py
│   └── white_bg_processor.py
├── qml/
│   ├── Main.qml                  主窗口:侧边栏 + 主内容区
│   ├── tools_config.js           ⭐ 工具与分类的单一数据源
│   ├── components/
│   │   ├── SideBar.qml           分类折叠侧边栏(读取 tools_config)
│   │   └── ModernButton.qml      公用按钮组件
│   └── pages/                    每个工具一个页面文件
│       ├── ProductMatrixPage.qml
│       ├── ImageDistributorPage.qml
│       └── ...
├── .u2net/
│   └── u2net.onnx                抠图模型(约 170MB,不入库)
├── 发布与自动更新方案.md         GitHub Releases + 自动更新设计
└── README.md
```

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                         Main.qml                            │
│  ┌──────────────┐   ┌──────────────────────────────────┐    │
│  │   SideBar    │   │           StackLayout            │    │
│  │              │   │  ┌────────────────────────────┐  │    │
│  │  💼 工作      │   │  │   Loader(页面 1)         │  │    │
│  │   ├ 工具A    │◄──┼──┤   Loader(页面 2)         │  │    │
│  │   └ 工具B    │   │  │   ...                      │  │    │
│  │  🏠 日常      │   │  └────────────────────────────┘  │    │
│  └──────────────┘   └──────────────────────────────────┘    │
│              ▲                          ▲                   │
│              │ 读取                      │ 渲染              │
│              └──────  tools_config.js   ─┘                  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │  setContextProperty
                            │
┌─────────────────────────────────────────────────────────────┐
│                          main.py                            │
│  实例化各 Backend → 注册到 QML 引擎 → load(Main.qml)         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       backends/*.py                          │
│  每个工具一个 QObject 子类,暴露 Signal / Slot / Property    │
└─────────────────────────────────────────────────────────────┘
```

**关键点**

1. **`tools_config.js` 是唯一真相**。侧边栏从它读分类和工具,主内容区从它读页面路径。任何一个工具在工具箱中"存在",就是因为它在这个文件里有一项。
2. **侧边栏与页面顺序解耦**。`tools_config.js` 中分类的顺序、每个分类下工具的顺序就是页面在 `StackLayout` 中的顺序,无需手动同步。
3. **页面按需懒加载**(通过 `Loader`),启动更快,工具数量增长时不会拖慢冷启动。

---

## 分类体系

当前分为三大类(在 `tools_config.js` 中定义):

| 分类 | id     | 说明                                       |
|------|--------|--------------------------------------------|
| 工作 | work   | 上班用的、和业务流程相关的工具             |
| 日常 | daily  | 个人生活、文件整理、效率小工具             |
| 其他 | misc   | 暂时归类不明的、实验性的、临时工具         |

> 加新分类:在 `qml/tools_config.js` 的 `categories` 数组顶层加一项即可,字段为 `{ id, name, icon, tools: [] }`。

---

## 新增一个工具的标准流程

下面以"加一个 PDF 合并工具"为例,展示完整步骤。所有新工具都按这四步走。

### 1. 写后端

新建 `backends/pdf_merger.py`:

```python
# -*- coding: utf-8 -*-
from PySide6.QtCore import QObject, Signal, Slot, Property


class PdfMergerBackend(QObject):
    progressChanged = Signal(int)        # 0-100
    finished = Signal(str)               # 输出路径或错误消息
    statusChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._status = "就绪"

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Slot(list, str)
    def merge(self, input_files: list, output_path: str):
        # 实际业务逻辑放这里。建议用 QThread 或线程池避免阻塞 UI
        ...
```

**约定**

- 所有公开方法用 `@Slot(...)` 装饰,标明参数类型
- 长任务必须放线程,通过 `Signal` 把进度推回 UI
- 后端不 import QML,不依赖任何前端

### 2. 写页面

新建 `qml/pages/PdfMergerPage.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label { text: "PDF 合并"; font.pixelSize: 22; font.bold: true }

        // ... 文件选择、参数配置、开始按钮 ...

        ProgressBar { from: 0; to: 100; value: 0; Layout.fillWidth: true }
    }

    Connections {
        target: pdfMerger          // 与 main.py 中 setContextProperty 的名字对应
        function onProgressChanged(v) { /* 更新 UI */ }
        function onFinished(msg)      { /* 提示用户 */ }
    }
}
```

**约定**

- 页面根元素用 `Item`(不用 `ApplicationWindow`)
- 每个页面自己管自己的状态,不跨页面共享
- 引用后端用 `setContextProperty` 注册的全局名,大小写要一致

### 3. 在 `main.py` 注册后端

```python
from backends.pdf_merger import PdfMergerBackend

# main() 函数里,和其他 backend 放一起:
pdf_merger = PdfMergerBackend()
ctx.setContextProperty("pdfMerger", pdf_merger)
```

### 4. 在 `tools_config.js` 加配置

```js
// 在合适的分类(比如 daily)的 tools 数组里加:
{
    id: "pdf-merger",
    name: "PDF 合并",
    icon: "📄",
    page: "pages/PdfMergerPage.qml",
    tags: ["PDF", "合并"]
}
```

完成。重新运行 `python main.py`,侧边栏自动多出这一项。

> ⚠️ **不需要改任何其他文件**(`Main.qml`、`SideBar.qml` 都不动)。如果你发现需要改,说明架构被破坏了,要回头看看哪里写硬了。

---

## 代码风格与约定

### Python(后端)

- 文件头加 `# -*- coding: utf-8 -*-`
- 类名 `XxxBackend`,文件名 `xxx_backend.py` 或简写 `xxx.py`
- 信号、属性命名用驼峰(因为 QML 里要用),内部变量用下划线
- 长任务**必须**异步(QThread / threading),禁止阻塞主线程
- 第三方依赖在 `requirements.txt` 集中声明,不要散落

### QML(前端)

- 文件名 `XxxPage.qml`,根元素 `Item`
- 不在 QML 里写业务计算逻辑,只做展示和事件转发
- 公用组件放 `qml/components/`,只被自己用的内部组件就内联在 page 里
- 颜色尽量用现有调色板:主色 `#0078D4`、背景 `#F5F6F8`、卡片 `#FFFFFF`、文字 `#333333`、次级 `#666666`

### 文件资源

- 大模型、大素材**不入库**,通过 `.gitignore` 排除
- 程序首次运行时需要的资源,用"提示用户手动放置"或"启动时下载"两种方式

---

## 打包与发布

完整方案见 [发布与自动更新方案.md](./发布与自动更新方案.md)。简要流程:

1. 改完代码,更新 `main.py` 顶部的 `__version__`
2. `git commit && git tag v1.x.x && git push --tags`
3. GitHub Actions 自动打包并发布到 Releases
4. 用户旧版本启动时检测到新版,弹窗提示下载

---

## 给 AI 协作者的说明

> 这一节专门写给以后协作的 AI 看,帮你快速进入状态。

### 你最该先看的文件

按重要程度排序:

1. **`qml/tools_config.js`** —— 知道当前有哪些工具、归在哪个分类
2. **`main.py`** —— 知道每个 backend 在 QML 里叫什么名字
3. **`backends/<对应文件>.py`** —— 看具体业务逻辑
4. **`qml/pages/<对应文件>.qml`** —— 看 UI 怎么写的

### 改动时的注意事项

- **新增工具**:严格按上面"新增一个工具的标准流程"的四步走,不要试图直接改 `Main.qml` 或 `SideBar.qml`,它们是数据驱动的
- **改动现有工具**:绝大多数情况下只需要动 `backends/xxx.py` 和 `qml/pages/XxxPage.qml` 两个文件
- **重命名工具**:改 `tools_config.js` 的 `name` 字段就行,不要改文件名(会影响 git 历史)
- **删除工具**:从 `tools_config.js` 移除条目后,可以保留后端和页面文件作为参考,确认无用再清理
- **加分类**:`tools_config.js` 的 `categories` 数组顶层加一项

### 不要做的事

- ❌ 不要在 `SideBar.qml` 里硬编码工具名(已经全部数据化了)
- ❌ 不要在 `Main.qml` 里逐个写 `<XxxPage> {}`(已经用 `Repeater` + `Loader` 自动渲染)
- ❌ 不要在 backend 里 `import` QML 相关的东西(违反分层)
- ❌ 不要为单个工具单独建仓库(本项目就是聚合仓库)
- ❌ 不要把 `.u2net/u2net.onnx` 之类的大文件提交到 git

### 常见任务速查

| 任务                       | 改哪些文件                                                  |
|----------------------------|------------------------------------------------------------|
| 加一个新工具               | `backends/x.py` + `qml/pages/XPage.qml` + `main.py` + `tools_config.js` |
| 加一个新分类               | `qml/tools_config.js`                                      |
| 调整工具顺序 / 改归类      | `qml/tools_config.js`                                      |
| 改某工具的展示名 / 图标    | `qml/tools_config.js`                                      |
| 修改某工具的逻辑           | 对应 `backends/x.py`                                       |
| 修改某工具的界面           | 对应 `qml/pages/XPage.qml`                                 |
| 改全局配色 / 主窗口尺寸    | `qml/Main.qml`                                             |
| 改侧边栏样式               | `qml/components/SideBar.qml`                               |

---

## License

私有项目,内部使用。
