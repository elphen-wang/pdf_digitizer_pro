# 开发说明 / Development Guide

## 代码规范 / Code Standards

### 类型提示 / Type Hints

所有函数必须包含完整的类型提示：

```python
def process_data(
    self,
    x: float,
    y: float,
    scale: Optional[float] = None
) -> Tuple[float, float]:
    """Process data with type hints."""
    pass
```

### 文档字符串 / Docstrings

使用Google风格的文档字符串：

```python
def calculate_distance(
    point1: Tuple[float, float],
    point2: Tuple[float, float]
) -> float:
    """Calculate Euclidean distance between two points.
    
    Args:
        point1: First point as (x, y) tuple
        point2: Second point as (x, y) tuple
        
    Returns:
        Euclidean distance between the points
        
    Raises:
        ValueError: If points are invalid
    """
    pass
```

### 命名规范 / Naming Conventions

- **类名**：PascalCase（如 `PDFProcessor`）
- **函数/方法名**：snake_case（如 `process_data`）
- **常量**：UPPER_SNAKE_CASE（如 `MAX_SCALE`）
- **私有方法**：以单下划线开头（如 `_internal_method`）

### 模块化设计原则 / Modular Design Principles

- **单一职责**：每个模块/类只负责一个功能
- **低耦合**：模块间依赖最小化
- **高内聚**：相关功能集中在同一模块
- **可测试性**：便于单元测试

## 开发环境设置 / Development Environment Setup

### 1. 克隆项目

```bash
git clone https://github.com/elphen-wang/pdf_digitizer_pro.git
cd pdf_digitizer_pro
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 安装开发工具（可选）

```bash
pip install mypy pylint black
```

## 代码检查 / Code Checking

### 类型检查

```bash
mypy .
```

### 代码质量检查

```bash
pylint core/ ui/ utils/
```

### 代码格式化

```bash
black .
```

## 测试 / Testing

### 运行测试

```bash
python -m pytest tests/
```

### 测试覆盖率

```bash
pytest --cov=core --cov=ui --cov=utils
```

## 贡献指南 / Contributing

### 提交代码

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 代码审查标准

- 代码符合项目规范
- 包含必要的测试
- 更新相关文档
- 通过所有检查

### 报告问题

使用 GitHub Issues 报告问题，包括：
- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息

## 版本管理 / Version Management

### 版本号格式

遵循语义化版本（Semantic Versioning）：
- MAJOR.MINOR.PATCH
- 例如：1.2.3

### 发布流程

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git tag
4. 发布到 GitHub Releases

## 性能优化建议 / Performance Optimization Tips

### 图像处理

- 使用适当的插值方法（LANCZOS用于质量，NEAREST用于速度）
- 缓存处理后的图像
- 避免不必要的图像缩放

### 事件处理

- 使用节流机制减少事件处理频率
- 避免在事件处理中进行耗时操作
- 使用异步处理长时间任务

### 内存管理

- 及时释放不需要的资源
- 避免内存泄漏
- 使用生成器处理大数据集

## 调试技巧 / Debugging Tips

### 日志记录

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

### 断点调试

使用 IDE 的调试功能或 pdb：

```python
import pdb
pdb.set_trace()
```

## 常见问题 / FAQ

### Q: 如何添加新的语言支持？

A: 在 `config.py` 的 `LANG_MAP` 中添加新的语言代码和对应的翻译。

### Q: 如何修改图像处理参数？

A: 在 `config.py` 中修改相关常量，如 `IMAGE_INTERPOLATION`。

### Q: 如何扩展数据导出格式？

A: 在 `ui/components.py` 的 `DataWindow` 类中添加新的导出方法。

## 参考资源 / References

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Pillow Documentation](https://pillow.readthedocs.io/)

