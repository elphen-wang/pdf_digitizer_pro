# 项目架构 / Project Architecture

## 项目结构 / Project Structure

```
pdf_digitizer_pro/
├── main.py                 # 程序入口 / Program entry point
├── config.py              # 配置和常量 / Configuration and constants
├── requirements.txt        # 依赖列表 / Dependencies
├── .gitignore             # Git忽略文件 / Git ignore file
├── core/                  # 核心处理模块 / Core processing modules
│   ├── __init__.py
│   ├── pdf_processor.py   # PDF处理和图像操作 / PDF processing and image operations
│   ├── calibration.py     # 坐标标定逻辑 / Coordinate calibration logic
│   └── data_extractor.py # 曲线提取和数据转换 / Curve extraction and data transformation
├── ui/                    # UI模块 / UI modules
│   ├── __init__.py
│   ├── components.py      # UI组件（输入框、放大镜、数据窗口） / UI components
│   └── main_window.py     # 主窗口和应用类 / Main window and application class
└── utils/                 # 工具模块 / Utility modules
    ├── __init__.py
    └── helpers.py         # 工具函数 / Helper functions
```

## 模块说明 / Module Description

### core/ - 核心处理模块

- **pdf_processor.py**: 负责PDF文件的加载、页面渲染和图像处理
- **calibration.py**: 管理坐标轴标定状态和计算
- **data_extractor.py**: 处理曲线数据的提取和坐标转换

### ui/ - 用户界面模块

- **components.py**: 可复用的UI组件（输入框、放大镜、数据窗口）
- **main_window.py**: 主应用程序窗口，协调所有模块

### utils/ - 工具模块

- **helpers.py**: 通用工具函数（坐标转换、数值映射等）

### config.py

集中管理所有配置常量，包括：
- 语言映射
- UI常量
- PDF处理参数
- 图像处理设置

## 代码优化说明 / Code Optimization

本项目已进行全面重构和优化：

### 模块化设计 / Modular Design

- 将原单文件（692行）拆分为清晰的模块结构
- 每个模块职责单一，便于维护和测试
- 清晰的依赖关系，降低耦合度

### 类型提示 / Type Hints

- 所有函数都添加了完整的类型提示
- 提升代码可读性和IDE支持
- 便于静态类型检查

### 文档完善 / Documentation

- 所有类和方法都包含详细的文档字符串（Google风格）
- 模块级文档说明
- 参数和返回值说明

### 错误处理 / Error Handling

- 改进的异常处理机制
- 使用具体异常类型而非通用Exception
- 用户友好的错误提示信息

### 性能优化 / Performance

- 优化的图像缩放算法（可配置插值方法）
- 鼠标事件节流机制（减少不必要的更新）
- 高效的数据筛选算法
- 视图图像缓存机制

### 配置管理 / Configuration Management

- 所有魔法数字提取为配置常量
- 集中管理，便于调整和扩展
- 支持运行时配置

## 技术特性 / Technical Features

### 模块化架构

- **清晰的代码结构**：易于理解和维护
- **低耦合高内聚**：模块间依赖最小化
- **易于扩展**：新功能可以轻松添加

### 类型安全

- **完整的类型提示**：提升代码质量
- **IDE支持**：更好的自动补全和错误检测
- **文档化**：类型即文档

### 性能优化

- **图像处理优化**：使用高效的插值算法
- **事件处理优化**：节流机制减少CPU占用
- **内存管理**：及时释放资源

### 错误处理

- **完善的异常处理**：覆盖所有可能的错误情况
- **用户友好提示**：清晰的错误信息
- **优雅降级**：错误不影响程序稳定性

### 配置灵活

- **集中管理**：所有配置在一个文件中
- **易于调整**：修改配置无需改动代码
- **可扩展性**：支持添加新配置项

## 依赖项 / Dependencies

### 核心依赖

- **PyMuPDF (fitz) >= 1.23.0**
  - PDF文件解析和处理
  - 矢量绘图数据提取
  - 页面渲染为图像

- **Pillow >= 10.0.0**
  - 图像处理和转换
  - 图像缩放和裁剪
  - 图像格式支持

- **Tkinter**
  - GUI框架（Python标准库）
  - 窗口和控件管理
  - 事件处理

### 可选依赖

- **类型检查工具**（开发时）
  - mypy: 静态类型检查
  - pylint: 代码质量检查

## 数据流 / Data Flow

```
PDF文件
  ↓
PDFProcessor (加载和渲染)
  ↓
图像显示在Canvas
  ↓
用户标定坐标轴
  ↓
CalibrationState (存储标定信息)
  ↓
用户点击曲线
  ↓
DataExtractor (提取和转换数据)
  ↓
DataWindow (显示和导出)
```

## 设计模式 / Design Patterns

- **MVC模式**：分离数据、视图和控制逻辑
- **单例模式**：配置和状态管理
- **观察者模式**：事件驱动的UI更新
- **策略模式**：可配置的图像处理算法

