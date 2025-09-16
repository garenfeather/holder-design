#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
包装展开模板变换器 (二进制复制版)
功能：直接二进制复制PSD文件，然后在复制的文件上进行变换

简化流程：
1. 读取模板psd，检测必要图层
2. 二进制复制PSD文件到输出位置
3. 在复制的PSD文件上应用变换（画布扩展、图层移动、翻转）
4. 保存修改后的PSD文件
"""

from psd_tools import PSDImage
from PIL import Image, ImageOps
import shutil
import struct
import io
from pathlib import Path

class BinaryPSDTransformer:
    def __init__(self, input_path, output_path=None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self._generate_output_path()
        self.required_layers = ["view", "part1", "part2", "part3", "part4"]
        
    def _generate_output_path(self):
        """生成输出文件路径"""
        return self.input_path.with_name(f"{self.input_path.stem}_transformed.psd")
    
    def step1_validate_and_copy(self):
        """1. 验证输入PSD并二进制复制到输出位置"""
        print(f"📂 步骤1：读取并验证模板PSD: {self.input_path}")
        
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
            print(f"\n❌ 模板PSD缺少以下必要图层:")
            for missing in missing_layers:
                print(f"    • {missing}")
            return False
        
        self.layers = found_layers
        print("  图层验证: ✓ 所有必要图层都已找到")
        return True
    
    def step2_calculate_transformations(self):
        """2. 计算所有变换参数"""
        print(f"\n📐 步骤2：计算变换参数...")
        
        # 获取各part图层的尺寸
        self.part_bounds = {}
        for part_name in ['part1', 'part2', 'part3', 'part4']:
            bounds = self._get_layer_bounds(self.layers[part_name])
            if not bounds:
                raise ValueError(f"无法获取 {part_name} 的边界信息")
            self.part_bounds[part_name] = bounds
            print(f"  {part_name} 尺寸: {bounds['width']}×{bounds['height']} px")
        
        # 计算新画布尺寸
        view_bounds = self._get_layer_bounds(self.layers['view'])
        if not view_bounds:
            raise ValueError("无法获取 view 的边界信息")
        view_width = view_bounds['width']
        view_height = view_bounds['height']

        part1_width = self.part_bounds['part1']['width']
        part2_height = self.part_bounds['part2']['height']
        part3_width = self.part_bounds['part3']['width']
        part4_height = self.part_bounds['part4']['height']

        new_width = view_width + part1_width + part3_width + 400
        new_height = view_height + part2_height + part4_height + 400
        
        original_width = self.psd.width
        original_height = self.psd.height
        
        self.original_size = (original_width, original_height)
        self.new_size = (new_width, new_height)
        self.center_offset_x = (new_width - original_width) // 2
        self.center_offset_y = (new_height - original_height) // 2
        
        print(f"  原始画布尺寸: {original_width}×{original_height} px")
        print(f"  新画布尺寸: {new_width}×{new_height} px") 
        print(f"  中心偏移量: X: +{self.center_offset_x} px, Y: +{self.center_offset_y} px")
        
        # 计算每个图层的最终位置
        self._calculate_final_positions()
        return True
    
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
    
    def _calculate_final_positions(self):
        """计算所有图层的最终位置"""
        print(f"\n🚀 计算图层最终位置...")
        
        self.final_positions = {}
        
        for layer in self.psd:
            layer_name = layer.name.lower()
            bounds = self._get_layer_bounds(layer)
            if not bounds:
                continue
            
            # 先应用中心偏移
            centered_x = bounds['x1'] + self.center_offset_x  
            centered_y = bounds['y1'] + self.center_offset_y
            
            # 再应用移动
            if layer_name == 'part1':
                final_x = centered_x - self.part_bounds['part1']['width']
                final_y = centered_y
            elif layer_name == 'part2':
                final_x = centered_x
                final_y = centered_y - self.part_bounds['part2']['height']
            elif layer_name == 'part3':
                final_x = centered_x + self.part_bounds['part3']['width'] 
                final_y = centered_y
            elif layer_name == 'part4':
                final_x = centered_x
                final_y = centered_y + self.part_bounds['part4']['height']
            else:
                final_x = centered_x
                final_y = centered_y
            
            self.final_positions[layer.name] = {
                'original_pos': (bounds['x1'], bounds['y1']),
                'centered_pos': (centered_x, centered_y),
                'final_pos': (final_x, final_y),
                'needs_flip': layer_name in ['part1', 'part2', 'part3', 'part4'],
                'flip_type': 'horizontal' if layer_name in ['part1', 'part3'] else 'vertical' if layer_name in ['part2', 'part4'] else None
            }
            
            move_info = f"  {layer.name}: ({bounds['x1']},{bounds['y1']}) → 中心对齐({centered_x},{centered_y}) → 最终({final_x},{final_y})"
            if self.final_positions[layer.name]['flip_type']:
                move_info += f" [{self.final_positions[layer.name]['flip_type']}翻转]"
            print(move_info)
    
    def step3_apply_transformations(self):
        """3. 在复制的PSD文件上应用变换"""
        print(f"\n💾 步骤3：在复制的PSD文件上应用变换...")
        
        try:
            # 修改PSD文件的画布尺寸和图层位置
            self._modify_psd_binary()
            print(f"  ✓ 变换已应用到: {self.output_path}")
            print(f"  ✓ 画布尺寸: {self.original_size[0]}×{self.original_size[1]} → {self.new_size[0]}×{self.new_size[1]}")
            print(f"  ✓ 包含 {len(self.final_positions)} 个变换后的图层")
            return True
        except Exception as e:
            print(f"❌ 应用变换失败: {e}")
            return False
    
    def _modify_psd_binary(self):
        """直接修改PSD文件的二进制数据"""
        print("  开始修改PSD二进制数据...")
        
        # 提取原始PSD的分辨率信息
        self.original_resolution = self._extract_resolution_from_psd(self.input_path)
        print(f"  提取原始分辨率: {self.original_resolution['h_res']:.1f} × {self.original_resolution['v_res']:.1f} DPI")
        
        # 这里使用简单的方法：重新提取图层，应用变换，然后保存
        # 创建新的变换后的图层数据
        transformed_layers = []
        
        for layer in self.output_psd:
            if layer.name in self.final_positions:
                pos_info = self.final_positions[layer.name]
                
                # 获取图层图像
                layer_image = layer.composite()
                if layer_image and pos_info['needs_flip']:
                    # 应用翻转
                    if pos_info['flip_type'] == 'horizontal':
                        layer_image = ImageOps.mirror(layer_image)
                    elif pos_info['flip_type'] == 'vertical':
                        layer_image = ImageOps.flip(layer_image)
                
                if layer_image:
                    if layer_image.mode != 'RGBA':
                        layer_image = layer_image.convert('RGBA')
                    
                    transformed_layers.append({
                        'name': layer.name,
                        'image': layer_image,
                        'position': pos_info['final_pos']
                    })
                    print(f"    处理图层: {layer.name}")
        
        # 创建新的PSD文件
        self._write_transformed_psd(transformed_layers)
    
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
    
    def _write_transformed_psd(self, layers_data):
        """写入变换后的PSD文件"""
        import io
        
        canvas_width, canvas_height = self.new_size
        
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
                self.original_resolution['h_res'],
                self.original_resolution['v_res'],
                self.original_resolution.get('h_res_unit', 1),
                self.original_resolution.get('v_res_unit', 1),
                self.original_resolution.get('width_unit', 1),
                self.original_resolution.get('height_unit', 1)
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
        """执行完整变换流程"""
        try:
            print("=" * 60)
            print("🎯 包装展开模板变换器 (二进制复制版)")
            print("=" * 60)
            
            # 1. 验证并二进制复制
            if not self.step1_validate_and_copy():
                return False
            
            # 2. 计算变换参数
            if not self.step2_calculate_transformations():
                return False
            
            # 3. 应用变换
            if not self.step3_apply_transformations():
                return False
            
            print("\n" + "=" * 60)
            print("✅ 变换完成!")
            print(f"📁 输入文件: {self.input_path.name}")
            print(f"📁 输出文件: {self.output_path.name}")
            print(f"📐 画布尺寸: {self.original_size[0]}×{self.original_size[1]} → {self.new_size[0]}×{self.new_size[1]}")
            print(f"🎯 中心偏移: X: +{self.center_offset_x}, Y: +{self.center_offset_y}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ 变换过程中出现错误: {e}")
            return False

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python transform_to_outside.py <输入PSD文件> [输出文件]")
        print("示例: python transform_to_outside.py input.psd")
        print("示例: python transform_to_outside.py input.psd output_transformed.psd")
        return 1
    
    try:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        # 检查输入文件
        if not Path(input_file).exists():
            print(f"❌ 未找到输入文件: {input_file}")
            return 1
        
        # 创建变换器
        transformer = BinaryPSDTransformer(input_file, output_file)
        
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