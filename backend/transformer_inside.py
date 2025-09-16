#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inside Layer Transformer
功能：将PSD文件中的part图层向内翻转和移动

变换流程：
1. Detecting PSD file是否包含view、part1-4图层
2. Binary copying PSD file
3. 对图层进行翻转变换：
   - part1和part3: 以自身为中心原地horizontal flip180度
   - part2和part4: 以自身为中心原地上下翻转180度
4. 对图层进行移动：
   - part1: move right自身图层宽度
   - part3: move left自身图层宽度
   - part2: move down自身图层高度
   - part4: move up自身图层高度
5. 输出变换后的PSD文件
"""

from psd_tools import PSDImage
from utils.strings import sanitize_name
from PIL import Image, ImageOps
import shutil
import struct
import io
from pathlib import Path


class InsideTransformer:
    def transform(self, input_path, output_path):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.required_layers = ["view", "part1", "part2", "part3", "part4"]

        try:
            print("=" * 60)
            print("[PROCESS] Inside Layer Transformer")
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
            print("[SUCCESS] Inside transformation completed!")
            print(f"[FILE] Input file: {self.input_path.name}")
            print(f"[FILE] Output file: {self.output_path.name}")
            print(f"Canvas size: {self.psd.width}x{self.psd.height} (unchanged)")
            print("[PROCESS] Transformations:")
            print("  • part1/part3: horizontal flip + left/right move")
            print("  • part2/part4: vertical flip + up/down move")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error during transformation: {e}")
            import traceback
            traceback.print_exc()
            return False

    def step1_validate_psd(self):
        """1. Detecting PSD file是否包含必要图层"""
        print(f"Step 1: Detecting PSD file: {self.input_path}")
        
        # 验证Input file
        try:
            self.psd = PSDImage.open(str(self.input_path))
            print(f"  File loaded successfully: size {self.psd.width}×{self.psd.height} px")
        except Exception as e:
            print(f"[ERROR] Failed to load PSD file: {e}")
            return False
        
        # Detecting required layers
        if not self._detect_required_layers():
            return False
            
        return True
    
    def _detect_required_layers(self):
        """检测必要的图层"""
        print("[SEARCH] Detecting required layers...")
        
        found_layers = {}
        missing_layers = []
        
        for i, layer in enumerate(self.psd):
            layer_name = sanitize_name(layer.name).lower()
            if layer_name in self.required_layers:
                found_layers[layer_name] = layer
                print(f"  Found layer: {layer.name} (index: {i})")
        
        for required in self.required_layers:
            if required not in found_layers:
                missing_layers.append(required)
        
        if missing_layers:
            print(f"\n[ERROR] PSD file is missing required layers:")
            for missing in missing_layers:
                print(f"    • {missing}")
            return False
        
        self.layers = found_layers
        print("  Layer validation: All required layers found")
        return True
    
    def step2_copy_psd(self):
        """2. Binary copying PSD file"""
        print(f"\n📋 Step2：Binary copying PSD file...")
        try:
            # 直接二进制复制文件
            shutil.copy2(str(self.input_path), str(self.output_path))
            print(f"  ✓ File copied to: {self.output_path}")
            
            # 重新打开复制的文件进行操作
            self.output_psd = PSDImage.open(str(self.output_path))
            return True
        except Exception as e:
            print(f"[ERROR] File copy failed: {e}")
            return False
    
    def step3_analyze_layers(self):
        """3. Analyzing layer positions and sizes"""
        print(f"\n📐 Step3：Analyzing layer positions and sizes...")
        
        self.layer_info = {}
        
        for layer in self.psd:
            layer_name = sanitize_name(layer.name).lower()
            if layer_name in self.required_layers:
                bounds = self._get_layer_bounds(layer)
                if bounds:
                    self.layer_info[layer_name] = {
                        'bounds': bounds,
                        'position': (bounds['x1'], bounds['y1']),
                        'size': (bounds['width'], bounds['height'])
                    }
                    print(f"  {layer.name}: position({bounds['x1']}, {bounds['y1']}) size{bounds['width']}×{bounds['height']}")
        
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
        print(f"\n[PROCESS] Step4：Applying layer transformations...")
        
        # Calculating transformation parameters
        transformations = self._calculate_transformations()
        
        # Creating transformed layer data
        transformed_layers = self._create_transformed_layers(transformations)
        
        # Writing transformed PSD file
        self._write_transformed_psd(transformed_layers)
        
        return True
    
    def _calculate_transformations(self):
        """计算每个图层的变换参数"""
        print("  Calculating transformation parameters...")
        
        transformations = {}
        
        for layer_name in ['part1', 'part2', 'part3', 'part4']:
            if layer_name in self.layer_info:
                info = self.layer_info[layer_name]
                bounds = info['bounds']
                width, height = info['size']
                
                # 确定翻转类型
                if layer_name in ['part1', 'part3']:
                    flip_type = 'horizontal'
                    print(f"  {layer_name}: horizontal flip")
                else:  # part2, part4
                    flip_type = 'vertical'
                    print(f"  {layer_name}: vertical flip")
                
                # 计算移动距离
                if layer_name == 'part1':
                    move_x = width  # move right自身宽度
                    move_y = 0
                    print(f"  {layer_name}: move right {width} pixels")
                elif layer_name == 'part2':
                    move_x = 0
                    move_y = height  # move down自身高度
                    print(f"  {layer_name}: move down {height} pixels")
                elif layer_name == 'part3':
                    move_x = -width  # move left自身宽度
                    move_y = 0
                    print(f"  {layer_name}: move left {width} pixels")
                elif layer_name == 'part4':
                    move_x = 0
                    move_y = -height  # move up自身高度
                    print(f"  {layer_name}: move up {height} pixels")
                
                # 计算新position
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
        """Creating transformed layer data"""
        print("  Creating transformed layer data...")
        
        transformed_layers = []
        
        for layer in self.psd:
            layer_name = sanitize_name(layer.name).lower()
            
            # 获取图层图像
            layer_image = layer.composite()
            if not layer_image:
                continue
            
            if layer_image.mode != 'RGBA':
                layer_image = layer_image.convert('RGBA')
            
            # 确定position
            if layer_name in transformations:
                # part图层需要变换
                transform = transformations[layer_name]
                
                # 应用翻转
                if transform['flip_type'] == 'horizontal':
                    layer_image = ImageOps.mirror(layer_image)
                elif transform['flip_type'] == 'vertical':
                    layer_image = ImageOps.flip(layer_image)
                
                # 使用新position
                position = transform['new_position']
                print(f"    Transform layer: {layer.name} -> position {position}")
            else:
                # view图层和其他图层保持原position
                bounds = self._get_layer_bounds(layer)
                position = (bounds['x1'], bounds['y1']) if bounds else (0, 0)
                print(f"    Keep layer: {layer.name} -> position {position}")
            
            transformed_layers.append({
                'name': layer.name,
                'image': layer_image,
                'position': position
            })
        
        return transformed_layers
    
    def _write_transformed_psd(self, layers_data):
        """Writing transformed PSD file"""
        print("  Writing transformed PSD file...")
        
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
                        
                        # 转换固定点数为浮点数（32位固定点，小数点position为16位）
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
            print(f"  Warning：Cannot extract resolution info: {e}")
        
        # 默认返回72 DPI
        return {'h_res': 72.0, 'v_res': 72.0, 'h_res_unit': 1, 'v_res_unit': 1, 'width_unit': 1, 'height_unit': 1}
    
    def _create_resolution_resource(self, h_res, v_res, h_res_unit=1, v_res_unit=1, width_unit=1, height_unit=1):
        """创建分辨率资源数据"""
        resource_data = io.BytesIO()
        
        # 转换DPI为32位固定点数（小数点position为16位）
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
