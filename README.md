# ColorDeck - 多重免疫荧光图像配准与合并工具

[English](README_EN.md) | 简体中文

ColorDeck 是一个用于多重免疫荧光（Multiplex Immunofluorescence, MIF）图像配准与合并的 Python 工具。该工具能够自动对齐来自同一视野但不同通道的显微镜图像，并将它们合并为一张综合图像。

---

## 功能特性

- **自动图像配准**：基于 DAPI 通道实现精确的图像对齐
- **多种配准算法**：
  - ECC（Enhanced Correlation Coefficient）算法 - 高精度配准
  - 相位相关法（Phase Correlation）- 鲁棒性备用方案
- **多种运动模型**：支持平移（Translation）、欧氏（Euclidean）、仿射（Affine）变换
- **配准质量可视化**：自动生成配准效果预览图
- **批量处理**：一键处理文件夹内所有图像
- **自动尺寸匹配**：配准前自动将非参考图居中裁剪或重采样到参考尺寸
- **总览拼图输出**：自动生成包含所有输入荧光图和最终 merged 图的汇总图
- **详细日志**：记录每张图像的变换矩阵和配准分数

---

## 安装依赖

```bash
pip install opencv-python numpy
```

---

## 使用方法

### 基本用法

```bash
python merge_mif_images.py
```

使用默认参数运行，输入文件夹为 `ColorDeck_test image`，参考图像为 `1_Spleen_DAPI_Lamin B1_RF 775_下_20.0x.jpg`。

### 自定义参数

```bash
python merge_mif_images.py \
    --input-folder "your_image_folder" \
    --reference-image "reference_image.jpg" \
    --dapi-channel b \
    --motion translation \
    --output-dir merged_output
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input-folder` | `ColorDeck_test image` | 包含待处理图像的文件夹路径 |
| `--reference-image` | `1_Spleen_DAPI_Lamin B1_RF 775_下_20.0x.jpg` | 参考图像文件名（位于输入文件夹内） |
| `--dapi-channel` | `b` | DAPI 通道选择：`b`（蓝）、`g`（绿）、`r`（红） |
| `--motion` | `translation` | 配准运动模型：`translation`、`euclidean`、`affine` |
| `--output-dir` | `merged_output` | 输出目录名称 |

---

## 输出说明

程序会在输入文件夹内创建带时间戳的输出目录，结构如下：

```
merged_output_YYYYMMDD_HHMMSS/
├── aligned_images/           # 配准后的图像
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── registration_previews/    # 配准质量预览
│   ├── image1_registration_check.png
│   ├── image2_registration_check.png
│   └── ...
├── merged_image.png          # 合并后的最终图像
├── input_and_merged_overview.png  # 输入原图 + merged 图总览
└── transform_info.txt        # 变换矩阵与配准分数记录
```

### 输出文件说明

| 文件 | 说明 |
|------|------|
| `aligned_images/` | 存放所有配准后的图像 |
| `registration_previews/` | 配准效果可视化（红色=参考DAPI，绿色=对齐DAPI，黄色=重叠区域） |
| `merged_image.png` | 所有图像逐像素取最大值合并的结果 |
| `input_and_merged_overview.png` | 将全部输入荧光图像与最终 merged 图按网格拼接成一张总览图，便于快速比对 |
| `transform_info.txt` | 记录每张图像的配准方法、分数和变换矩阵 |

---

## 算法原理

### 图像配准流程

```
参考图像 ──┐
           ├── 提取DAPI通道 ── 归一化 ── 高斯模糊 ── ECC配准 ── 变换对齐
待配准图像 ─┘
```

### ECC 算法

ECC（Enhanced Correlation Coefficient）是一种基于亮度一致性的图像配准算法，具有以下优势：

- 对光照变化具有不变性
- 配准精度高
- 支持多种变换模型

算法迭代优化变换矩阵，使得待配准图像与参考图像之间的相关系数最大化。

### 相位相关法

当 ECC 算法失败时（仅限平移模型），程序会自动切换到相位相关法：

- 基于频域的平移估计
- 计算速度快
- 对噪声具有较好的鲁棒性

---

## 注意事项

1. **图像尺寸**：程序会在配准前自动将非参考图调整到参考尺寸，优先居中裁剪，必要时重采样；总览图中的输入图保持原始内容，仅做缩略显示
2. **参考图像选择**：建议选择 DAPI 信号清晰、背景干净的图像作为参考
3. **运动模型选择**：
   - `translation`：适用于仅存在平移的情况，速度最快
   - `euclidean`：适用于存在平移和旋转的情况
   - `affine`：适用于存在平移、旋转、缩放和剪切的情况
4. **内存占用**：处理大图像时可能需要较大内存

---

## 支持的图像格式

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- TIFF (`.tif`, `.tiff`)
- BMP (`.bmp`)

---

## 许可证

MIT License
