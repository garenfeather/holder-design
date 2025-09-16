#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图层向内变换器
功能：将PSD文件中的part图层向内翻转和移动

变换流程：
1. 检测PSD文件是否包含view、part1-4图层
2. 二进制复制PSD文件
3. 对图层进行翻转变换：
   - part1和part3: 以自身为中心原地水平翻转180度
   - part2和part4: 以自身为中心原地上下翻转180度
4. 对图层进行移动：
   - part1: 向右移动自身图层宽度
   - part3: 向左移动自身图层宽度
   - part2: 向下移动自身图层高度
   - part4: 向上移动自身图层高度
5. 输出变换后的PSD文件
"""

from psd_tools import PSDImage
from PIL import Image, ImageOps
import shutil
import struct
import io
from pathlib import Path


class TransformToInside:
    def __init__(self, input_path, output_path=None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self._generate_output_path()
        self.required_layers = ["view", "part1", "part2", "part3", "part4"]
        
    def _generate_output_path(self):
        """生成输出文件路径"""
        return self.input_path.with_name(f"{self.input_path.stem}_inside.psd")
    
    def step1_validate_psd(self):
        """1. 检测PSD文件是否包含必要图层"""
        print(f"📂 步骤1：检测PSD文件: {self.input_path}")
        
        # 验证输入文件
        try:
            self.psd = PSDImage.open(str(self.input_path))
            print(f"  文件加载成功: 尺寸 {self.psd.width}×{self.psd.height} px")
        except Exception as e:
            print(f"❌ 加载PSD文件失败: {e}")
            return False
        
        # 检测必要图层
        if not self._detect_required_layers():
            return False
            
        return True
    
    def _detect_required_layers(self):
        """检测必要的图层"""
        print("🔍 检测必要图层...")
        
        found_layers = {}
        missing_layers = []
        
        for i, layer in enumerate(self.psd):
            layer_name = layer.name.lower()
            if layer_name in self.required_layers:
                found_layers[layer_name] = layer
                print(f"  找到图层: {layer.name} (索引: {i})")
        
        for required in self.required_layers:
            if required not in found_layers:
                missing_layers.append(required)
        
        if missing_layers:
            print(f"\n❌ PSD文件缺少以下必要图层:")
            for missing in missing_layers:
                print(f"    • {missing}")
            return False
        
        self.layers = found_layers
        print("  图层验证: ✓ 所有必要图层都已找到")
        return True
    
    def step2_copy_psd(self):
        """2. 二进制复制PSD文件"""
        print(f"\n📋 步骤2：二进制复制PSD文件...")
        try:
            # 直接二进制复制文件
            shutil.copy2(str(self.input_path), str(self.output_path))
            print(f"  ✓ 文件已复制到: {self.output_path}")
            
            # 重新打开复制的文件进行操作
            self.output_psd = PSDImage.open(str(self.output_path))
            return True
        except Exception as e:
            print(f"❌ 文件复制失败: {e}")
            return False
    
    def step3_analyze_layers(self):
        """3. 分析图层位置和尺寸"""
        print(f"\n📐 步骤3：分析图层位置和尺寸...")
        
        self.layer_info = {}
        
        for layer in self.psd:
            layer_name = layer.name.lower()
            if layer_name in self.required_layers:
                bounds = self._get_layer_bounds(layer)
                if bounds:
                    self.layer_info[layer_name] = {
                        'bounds': bounds,
                        'position': (bounds['x1'], bounds['y1']),
                        'size': (bounds['width'], bounds['height'])
                    }
                    print(f"  {layer.name}: 位置({bounds['x1']}, {bounds['y1']}) 尺寸{bounds['width']}×{bounds['height']}")
        
        return len(self.layer_info) == len(self.required_layers)
    
    def _get_layer_bounds(self, layer):
        """获取图层边界"""
        try:
            if not layer.bbox:
                return None
            bbox = layer.bbox
            if len(bbox) >= 4:
                x1, y1, x2, y2 = bbox
                return {
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'width': x2 - x1, 'height': y2 - y1
                }
        except:
            pass
        return None
    
    def step4_transform_layers(self):
        """4. 对图层进行翻转和移动变换"""
        print(f"\n🔄 步骤4：应用图层变换...")
        
        # 计算变换参数
        transformations = self._calculate_transformations()
        
        # 创建变换后的图层数据
        transformed_layers = self._create_transformed_layers(transformations)
        
        # 写入变换后的PSD文件
        self._write_transformed_psd(transformed_layers)
        
        return True
    
    def _calculate_transformations(self):
        """计算每个图层的变换参数"""
        print("  计算变换参数...")
        
        transformations = {}
        
        for layer_name in ['part1', 'part2', 'part3', 'part4']:
            if layer_name in self.layer_info:
                info = self.layer_info[layer_name]
                bounds = info['bounds']
                width, height = info['size']
                
                # 确定翻转类型
                if layer_name in ['part1', 'part3']:
                    flip_type = 'horizontal'
                    print(f"  {layer_name}: 水平翻转")
                else:  # part2, part4
                    flip_type = 'vertical'
                    print(f"  {layer_name}: 垂直翻转")
                
                # 计算移动距离
                if layer_name == 'part1':
                    move_x = width  # 向右移动自身宽度
                    move_y = 0
                    print(f"  {layer_name}: 向右移动 {width} 像素")
                elif layer_name == 'part2':
                    move_x = 0
                    move_y = height  # 向下移动自身高度
                    print(f"  {layer_name}: 向下移动 {height} 像素")
                elif layer_name == 'part3':
                    move_x = -width  # 向左移动自身宽度
                    move_y = 0
                    print(f"  {layer_name}: 向左移动 {width} 像素")
                elif layer_name == 'part4':
                    move_x = 0
                    move_y = -height  # 向上移动自身高度
                    print(f"  {layer_name}: 向上移动 {height} 像素")
                
                # 计算新位置
                new_x = bounds['x1'] + move_x
                new_y = bounds['y1'] + move_y
                
                transformations[layer_name] = {
                    'flip_type': flip_type,
                    'move_x': move_x,
                    'move_y': move_y,
                    'new_position': (new_x, new_y)
                }
        
        return transformations
    
    def _create_transformed_layers(self, transformations):
        """创建变换后的图层数据"""
        print("  创建变换后的图层数据...")
        
        transformed_layers = []
        
        for layer in self.psd:
            layer_name = layer.name.lower()
            
            # 获取图层图像
            layer_image = layer.composite()
            if not layer_image:
                continue
            
            if layer_image.mode != 'RGBA':
                layer_image = layer_image.convert('RGBA')
            
            # 确定位置
            if layer_name in transformations:
                # part图层需要变换
                transform = transformations[layer_name]
                
                # 应用翻转
                if transform['flip_type'] == 'horizontal':
                    layer_image = ImageOps.mirror(layer_image)
                elif transform['flip_type'] == 'vertical':
                    layer_image = ImageOps.flip(layer_image)
                
                # 使用新位置
                position = transform['new_position']
                print(f"    变换图层: {layer.name} -> 位置 {position}")
            else:
                # view图层和其他图层保持原位置
                bounds = self._get_layer_bounds(layer)
                position = (bounds['x1'], bounds['y1']) if bounds else (0, 0)
                print(f"    保持图层: {layer.name} -> 位置 {position}")
            
            transformed_layers.append({
                'name': layer.name,
                'image': layer_image,
                'position': position
            })
        
        return transformed_layers
    
    def _write_transformed_psd(self, layers_data):
        """写入变换后的PSD文件"""
        print("  写入变换后的PSD文件...")
        
        canvas_width = self.psd.width
        canvas_height = self.psd.height
        
        # 提取原始分辨率信息
        original_resolution = self._extract_resolution_from_psd(self.input_path)
        
        with open(self.output_path, 'wb') as f:
            # PSD文件头
            f.write(b'8BPS')
            f.write(struct.pack('>H', 1))
            f.write(b'\x00' * 6)
            f.write(struct.pack('>H', 4))
            f.write(struct.pack('>I', canvas_height))
            f.write(struct.pack('>I', canvas_width))
            f.write(struct.pack('>H', 8))
            f.write(struct.pack('>H', 3))
            
            # 颜色模式数据段（空）
            f.write(struct.pack('>I', 0))
            
            # 图像资源段（包含分辨率信息）
            resolution_resource = self._create_resolution_resource(
                original_resolution['h_res'],
                original_resolution['v_res'],
                original_resolution.get('h_res_unit', 1),
                original_resolution.get('v_res_unit', 1),
                original_resolution.get('width_unit', 1),
                original_resolution.get('height_unit', 1)
            )
            f.write(struct.pack('>I', len(resolution_resource)))
            f.write(resolution_resource)
            
            # 图层和蒙版信息段
            layer_info = io.BytesIO()
            self._write_layer_info(layer_info, layers_data, canvas_width, canvas_height)
            layer_data = layer_info.getvalue()
            f.write(struct.pack('>I', len(layer_data)))
            f.write(layer_data)
            
            # 合成图像数据
            f.write(struct.pack('>H', 0))
            self._write_composite_image(f, layers_data, canvas_width, canvas_height)
    
    def _extract_resolution_from_psd(self, psd_path):
        """从PSD文件中提取分辨率信息"""
        try:
            with open(psd_path, 'rb') as f:
                # 读取文件头
                signature = f.read(4)
                if signature != b'8BPS':
                    return {'h_res': 72.0, 'v_res': 72.0, 'h_res_unit': 1, 'v_res_unit': 1}
                
                # 跳过版本(2) + 保留字段(6) + 通道数(2) + 高度(4) + 宽度(4) + 位深度(2) + 颜色模式(2)
                f.seek(4 + 2 + 6 + 2 + 4 + 4 + 2 + 2)
                
                # 跳过颜色模式数据段
                color_mode_len = struct.unpack('>I', f.read(4))[0]
                f.seek(f.tell() + color_mode_len)
                
                # 读取图像资源段
                resources_len = struct.unpack('>I', f.read(4))[0]
                resources_start = f.tell()
                
                # 在图像资源段中查找分辨率信息（Resource ID 1005）
                while f.tell() < resources_start + resources_len:
                    # 读取资源签名
                    if f.read(4) != b'8BIM':
                        break
                    
                    # 读取资源ID
                    resource_id = struct.unpack('>H', f.read(2))[0]
                    
                    # 读取资源名称长度
                    name_len = struct.unpack('>B', f.read(1))[0]
                    if name_len > 0:
                        f.read(name_len)
                    # 填充对齐
                    if (name_len + 1) % 2 != 0:
                        f.read(1)
                    
                    # 读取数据长度
                    data_len = struct.unpack('>I', f.read(4))[0]
                    
                    if resource_id == 1005:  # 分辨率信息
                        # 读取分辨率数据
                        h_res_fixed = struct.unpack('>I', f.read(4))[0]
                        h_res_unit = struct.unpack('>H', f.read(2))[0]
                        width_unit = struct.unpack('>H', f.read(2))[0]
                        v_res_fixed = struct.unpack('>I', f.read(4))[0]
                        v_res_unit = struct.unpack('>H', f.read(2))[0]
                        height_unit = struct.unpack('>H', f.read(2))[0]
                        
                        # 转换固定点数为浮点数（32位固定点，小数点位置为16位）
                        h_res = h_res_fixed / 65536.0
                        v_res = v_res_fixed / 65536.0
                        
                        return {
                            'h_res': h_res,
                            'v_res': v_res,
                            'h_res_unit': h_res_unit,
                            'v_res_unit': v_res_unit,
                            'width_unit': width_unit,
                            'height_unit': height_unit
                        }
                    else:
                        # 跳过其他资源数据
                        f.seek(f.tell() + data_len)
                        # 填充对齐
                        if data_len % 2 != 0:
                            f.read(1)
                
        except Exception as e:
            print(f"  警告：无法提取分辨率信息: {e}")
        
        # 默认返回72 DPI
        return {'h_res': 72.0, 'v_res': 72.0, 'h_res_unit': 1, 'v_res_unit': 1, 'width_unit': 1, 'height_unit': 1}
    
    def _create_resolution_resource(self, h_res, v_res, h_res_unit=1, v_res_unit=1, width_unit=1, height_unit=1):
        """创建分辨率资源数据"""
        resource_data = io.BytesIO()
        
        # 转换DPI为32位固定点数（小数点位置为16位）
        h_res_fixed = int(h_res * 65536)
        v_res_fixed = int(v_res * 65536)
        
        # 写入分辨率数据
        resource_data.write(struct.pack('>I', h_res_fixed))      # 水平分辨率
        resource_data.write(struct.pack('>H', h_res_unit))       # 水平分辨率单位
        resource_data.write(struct.pack('>H', width_unit))       # 宽度单位
        resource_data.write(struct.pack('>I', v_res_fixed))      # 垂直分辨率
        resource_data.write(struct.pack('>H', v_res_unit))       # 垂直分辨率单位
        resource_data.write(struct.pack('>H', height_unit))      # 高度单位
        
        # 创建完整的资源记录
        full_resource = io.BytesIO()
        full_resource.write(b'8BIM')                             # 资源签名
        full_resource.write(struct.pack('>H', 1005))             # 资源ID (分辨率)
        full_resource.write(struct.pack('>B', 0))                # 资源名称长度（空名称）
        full_resource.write(b'\x00')                             # 填充对齐
        
        data = resource_data.getvalue()
        full_resource.write(struct.pack('>I', len(data)))        # 数据长度
        full_resource.write(data)                                # 数据内容
        
        # 填充对齐
        if len(data) % 2 != 0:
            full_resource.write(b'\x00')
        
        return full_resource.getvalue()
    
    def _write_layer_info(self, f, layers_data, canvas_width, canvas_height):
        """写入图层信息"""
        # 图层信息长度占位符
        layer_info_start = f.tell()
        f.write(struct.pack('>I', 0))
        
        # 图层计数
        f.write(struct.pack('>h', -len(layers_data)))
        
        # 图层记录
        for layer in layers_data:
            x, y = layer['position']
            x = max(0, int(x))
            y = max(0, int(y))
            w, h = layer['image'].size
            
            # 确保边界在画布内
            if x + w > canvas_width:
                w = max(1, canvas_width - x)
            if y + h > canvas_height:
                h = max(1, canvas_height - y)
            
            # 图层边界
            f.write(struct.pack('>I', y))
            f.write(struct.pack('>I', x))
            f.write(struct.pack('>I', y + h))
            f.write(struct.pack('>I', x + w))
            
            # 通道数和信息
            f.write(struct.pack('>H', 4))
            channel_size = w * h + 2
            for channel_id in [-1, 0, 1, 2]:
                f.write(struct.pack('>h', channel_id))
                f.write(struct.pack('>I', channel_size))
            
            # 混合模式等
            f.write(b'8BIM')
            f.write(b'norm')
            f.write(struct.pack('>B', 255))  # 不透明度
            f.write(struct.pack('>B', 0))    # 剪切
            f.write(struct.pack('>B', 0))    # 标志
            f.write(struct.pack('>B', 0))    # 填充
            
            # 额外数据
            extra_start = f.tell()
            f.write(struct.pack('>I', 0))
            
            # 蒙版和混合范围（空）
            f.write(struct.pack('>I', 0))
            f.write(struct.pack('>I', 0))
            
            # 图层名称
            name_bytes = layer['name'].encode('ascii')[:255]
            f.write(struct.pack('>B', len(name_bytes)))
            f.write(name_bytes)
            
            # 填充
            total_name_len = 1 + len(name_bytes)
            padding = (4 - (total_name_len % 4)) % 4
            f.write(b'\x00' * padding)
            
            # 更新额外数据长度
            extra_end = f.tell()
            f.seek(extra_start)
            f.write(struct.pack('>I', extra_end - extra_start - 4))
            f.seek(extra_end)
        
        # 图层图像数据
        for layer in layers_data:
            self._write_layer_channels(f, layer, canvas_width, canvas_height)
        
        # 更新图层信息长度
        layer_info_end = f.tell()
        f.seek(layer_info_start)
        f.write(struct.pack('>I', layer_info_end - layer_info_start - 4))
        f.seek(layer_info_end)
    
    def _write_layer_channels(self, f, layer, canvas_width, canvas_height):
        """写入图层通道数据"""
        image = layer['image']
        x, y = layer['position']
        x = max(0, int(x))
        y = max(0, int(y))
        
        # 如果图层超出画布，需要裁剪
        if x >= canvas_width or y >= canvas_height:
            # 图层完全在画布外，写入空数据
            for _ in range(4):
                f.write(struct.pack('>H', 0))
            return
        
        # 裁剪图像以适应画布
        crop_width = min(image.width, canvas_width - x)
        crop_height = min(image.height, canvas_height - y)
        
        if crop_width != image.width or crop_height != image.height:
            image = image.crop((0, 0, crop_width, crop_height))
        
        pixels = list(image.getdata())
        
        # 写入4个通道：A, R, G, B
        for channel_idx in [3, 0, 1, 2]:
            f.write(struct.pack('>H', 0))  # 无压缩
            for pixel in pixels:
                f.write(struct.pack('>B', pixel[channel_idx]))
    
    def _write_composite_image(self, f, layers_data, canvas_width, canvas_height):
        """写入合成图像"""
        # 创建合成画布
        composite = Image.new('RGBA', (canvas_width, canvas_height), (255, 255, 255, 0))
        
        # 合成所有图层
        for layer in layers_data:
            x, y = layer['position']
            x = max(0, int(x))
            y = max(0, int(y))
            
            if x < canvas_width and y < canvas_height:
                composite.paste(layer['image'], (x, y), layer['image'])
        
        # 写入合成图像数据
        pixels = list(composite.getdata())
        for channel_idx in [0, 1, 2, 3]:  # R, G, B, A
            for pixel in pixels:
                f.write(struct.pack('>B', pixel[channel_idx]))
    
    def transform(self):
        """执行完整的向内变换流程"""
        try:
            print("=" * 60)
            print("🔄 图层向内变换器")
            print("=" * 60)
            
            # 1. 验证PSD文件
            if not self.step1_validate_psd():
                return False
            
            # 2. 二进制复制文件
            if not self.step2_copy_psd():
                return False
            
            # 3. 分析图层信息
            if not self.step3_analyze_layers():
                return False
            
            # 4. 应用变换
            if not self.step4_transform_layers():
                return False
            
            print("\n" + "=" * 60)
            print("✅ 向内变换完成!")
            print(f"📁 输入文件: {self.input_path.name}")
            print(f"📁 输出文件: {self.output_path.name}")
            print(f"📐 画布尺寸: {self.psd.width}×{self.psd.height} (保持不变)")
            print("🔄 变换内容:")
            print("  • part1/part3: 水平翻转 + 左右移动")
            print("  • part2/part4: 垂直翻转 + 上下移动")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ 变换过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python transform_to_inside.py <输入PSD文件> [输出文件]")
        print("示例: python transform_to_inside.py input.psd")
        print("示例: python transform_to_inside.py input.psd output_inside.psd")
        return 1
    
    try:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        # 检查输入文件
        if not Path(input_file).exists():
            print(f"❌ 未找到输入文件: {input_file}")
            return 1
        
        # 创建变换器
        transformer = TransformToInside(input_file, output_file)
        
        # 执行变换
        success = transformer.transform()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())