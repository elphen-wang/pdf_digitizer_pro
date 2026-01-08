# PDF Vector Curve Extractor
A GUI tool to extract vector curve data from PDF files. Users can open PDFs, calibrate axes (linear/log scale), and pick curves to capture coordinate points. Features include data filtering, preview, copy, and export to TXT/CSV. Supports English/Chinese UI and offers a magnifier for precise selection. It can be considered a supplement and alternative to webplotdigitizer （https://automeris.io）.


## 中文说明

### 程序简介

本程序是一个基于Python的PDF矢量曲线提取工具，使用PyMuPDF解析PDF中的矢量绘图数据，结合Tkinter构建图形用户界面，方便用户从PDF图表中提取曲线的数值数据。可以当做是webplotdigitizer （https://automeris.io） 的补充和平替。

### 主要功能

1. **打开PDF文件并加载页面**  
   支持选择PDF文件，自动渲染页面为图像并提取矢量绘图信息。

2. **坐标轴标定**  
   用户通过点击PDF中四个关键点完成X轴和Y轴的坐标标定，支持线性和对数坐标。  
   通过输入实际坐标值，实现PDF坐标到真实数据坐标的映射。

3. **曲线数据提取**  
   在标定完成后，用户点击PDF页面上的目标曲线，程序自动识别附近的矢量路径，并提取曲线的所有点坐标。

4. **数据展示与筛选**  
   提取的数据会在独立窗口以表格形式展示，用户可以根据X、Y范围筛选数据，还可以设置采样间隔实现数据稀疏。

5. **数据导出和复制**  
   支持将筛选后的数据复制到剪贴板，或导出为TXT/CSV文件，方便后续分析。

6. **放大镜辅助定位**  
   鼠标移动时显示放大镜，辅助用户准确点击标定点或曲线，提高操作精度。

7. **多语言支持**  
   界面支持中文和英文两种语言切换，方便不同语言用户使用。

### 适用场景

- 从科研论文或报告中的PDF图表提取数值曲线数据  
- 工程图纸或技术文档中的曲线数据数字化  
- 教育和数据分析中需要手动或半自动采集图形数据的场合

---

## English Description

### Program Overview

This program is a Python-based PDF vector curve extractor that uses PyMuPDF to parse vector drawing data from PDF files and Tkinter for the graphical user interface. It enables users to extract numerical data points from curves embedded in PDF charts effortlessly.

### Key Features

1. **Load PDF files and pages**  
   Users can open a PDF document; the program renders the selected page as an image and extracts vector drawing information.

2. **Axis Calibration**  
   Users calibrate the X and Y axes by clicking four reference points on the PDF and entering their real-world coordinate values. Supports both linear and logarithmic scales.  
   This maps PDF coordinates to actual data coordinates.

3. **Curve Data Extraction**  
   After calibration, users can click on a curve in the PDF page, and the program will identify the nearest vector path and extract all coordinate points of the curve.

4. **Data Display and Filtering**  
   Extracted data is displayed in a separate window as a table. Users can filter data by X and Y ranges and define sampling strides to downsample points.

5. **Data Export and Copy**  
   Filtered data can be copied to the clipboard or exported as TXT/CSV files for further analysis.

6. **Magnifier for Precise Selection**  
   A magnifying glass appears near the cursor during calibration and picking, assisting users in precise point selection.

7. **Multilingual Support**  
   Interface supports both English and Chinese language toggling for user convenience.

### Use Cases

- Extracting numerical curve data from charts in scientific papers or reports (PDFs)  
- Digitizing curve data from engineering drawings or technical documents  
- Educational and data analysis scenarios requiring manual or semi-automatic graph digitization


## Example

<img width="1280" height="670" alt="image" src="https://github.com/user-attachments/assets/12447315-2ea3-48b9-8a12-487379545e38" />

<img width="1280" height="671" alt="image" src="https://github.com/user-attachments/assets/31048eea-9689-4389-a908-ad113a789610" />

ps: The figure of this example is taken from https://arxiv.org/abs/2411.11749 .

## Cite this project

```
@misc{pdf_digitizer_pro2026,
  author       = {J. Wang},
  title        = {{PDF Vector Curve Extractor}},
  howpublished = {\url{https://github.com/elphen-wang/pdf_digitizer_pro}},
  year         = {2026},
  note         = {Accessed: 2026-01-08}
}
```



