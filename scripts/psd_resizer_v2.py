#!/usr/bin/env python3
"""
PSD文件尺寸调整工具 V2
直接修改PSD二进制数据，保留完整图层结构
"""

import sys
import struct
from pathlib import Path


class PSDResizerV2:
    def __init__(self, input_path, target_width, target_height, output_path=None):
        self.input_path = Path(input_path)
        self.target_width = target_width
        self.target_height = target_height
        self.output_path = Path(output_path) if output_path else self._generate_output_path()
        
    def _generate_output_path(self):
        stem = self.input_path.stem
        suffix = self.input_path.suffix
        return self.input_path.parent / f"{stem}_resized_{self.target_width}x{self.target_height}{suffix}"
    
    def resize_psd(self):
        """直接修改PSD二进制数据调整尺寸"""
        print(f"📖 读取PSD二进制数据: {self.input_path}")
        
        try:
            with open(self.input_path, 'rb') as f:
                data = bytearray(f.read())
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return False
        
        print(f"  文件大小: {len(data)} bytes")
        
        # 验证PSD文件头
        if data[0:4] != b'8BPS':
            print("❌ 不是有效的PSD文件")
            return False
        
        # 读取原始尺寸
        original_height = struct.unpack('>I', data[14:18])[0]
        original_width = struct.unpack('>I', data[18:22])[0]
        
        print(f"  原始尺寸: {original_width} × {original_height}")
        print(f"  目标尺寸: {self.target_width} × {self.target_height}")
        
        if original_width == self.target_width and original_height == self.target_height:
            print("  ✅ 尺寸已匹配，直接复制")
            import shutil
            shutil.copy2(self.input_path, self.output_path)
            return True
        
        # 计算缩放比例
        scale_x = self.target_width / original_width
        scale_y = self.target_height / original_height
        print(f"  缩放比例: X={scale_x:.4f}, Y={scale_y:.4f}")
        
        # 修改文件头中的尺寸
        print("🔧 修改PSD文件头...")
        struct.pack_into('>I', data, 14, self.target_height)  # 高度
        struct.pack_into('>I', data, 18, self.target_width)   # 宽度
        print(f"  ✓ 画布尺寸已更新")
        
        # 修改图层位置和边界
        self._update_layer_bounds(data, scale_x, scale_y)
        
        # 保存修改后的文件
        try:
            with open(self.output_path, 'wb') as f:
                f.write(data)
            print(f"✅ 已保存到: {self.output_path}")
            
            # 验证文件
            self._verify_psd(self.output_path)
            return True
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def _update_layer_bounds(self, data, scale_x, scale_y):
        """更新图层边界信息"""
        print("🔧 更新图层边界...")
        
        try:
            # 跳过文件头部分，找到图层信息
            offset = 26  # 跳过文件头
            
            # 跳过色彩模式数据段
            color_mode_length = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4 + color_mode_length
            
            # 跳过图像资源段
            image_resources_length = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4 + image_resources_length
            
            # 图层和蒙版信息段
            layer_mask_length = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4
            
            if layer_mask_length == 0:
                print("  ⚠️ 无图层信息，这是扁平化PSD")
                return
            
            layer_info_start = offset
            layer_info_length = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4
            
            if layer_info_length == 0:
                print("  ⚠️ 图层信息为空")
                return
            
            # 读取图层数量
            layer_count = struct.unpack('>h', data[offset:offset+2])[0]
            if layer_count < 0:
                layer_count = abs(layer_count)  # 负数表示有alpha通道
            
            offset += 2
            print(f"  发现 {layer_count} 个图层")
            
            # 处理每个图层的边界
            for i in range(layer_count):
                print(f"    处理图层 {i+1}...")
                
                # 读取原始边界
                top = struct.unpack('>I', data[offset:offset+4])[0]
                left = struct.unpack('>I', data[offset+4:offset+8])[0]
                bottom = struct.unpack('>I', data[offset+8:offset+12])[0]
                right = struct.unpack('>I', data[offset+12:offset+16])[0]
                
                # 计算新边界
                new_top = int(top * scale_y)
                new_left = int(left * scale_x)
                new_bottom = int(bottom * scale_y)
                new_right = int(right * scale_x)
                
                # 写入新边界
                struct.pack_into('>I', data, offset, new_top)
                struct.pack_into('>I', data, offset+4, new_left)
                struct.pack_into('>I', data, offset+8, new_bottom)
                struct.pack_into('>I', data, offset+12, new_right)
                
                print(f"      边界: ({left},{top},{right},{bottom}) -> ({new_left},{new_top},{new_right},{new_bottom})")
                
                offset += 16
                
                # 跳过通道信息
                num_channels = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2 + (num_channels * 6)  # 每个通道6字节
                
                # 跳过混合模式签名等
                offset += 16  # 混合模式、不透明度等
                
                # 跳过额外数据
                extra_data_length = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4 + extra_data_length
            
            print(f"  ✓ 已更新 {layer_count} 个图层边界")
            
        except Exception as e:
            print(f"  ❌ 更新图层边界失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _verify_psd(self, psd_path):
        """验证生成的PSD文件"""
        try:
            from psd_tools import PSDImage
            
            psd = PSDImage.open(str(psd_path))
            print(f"  ✅ 验证成功: {psd.width}×{psd.height}")
            
            layer_names = [layer.name for layer in psd]
            print(f"  📋 图层列表: {layer_names}")
            
            # 检查part图层
            part_layers = [name for name in layer_names if name.lower() in ['part1', 'part2', 'part3', 'part4']]
            if part_layers:
                print(f"  ✅ 发现part图层: {part_layers}")
            else:
                print(f"  ⚠️ 未发现part图层")
            
        except Exception as e:
            print(f"  ⚠️ 验证失败: {e}")


def main():
    if len(sys.argv) < 4:
        print("用法: python psd_resizer_v2.py <输入PSD> <目标宽度> <目标高度> [输出文件]")
        return
    
    input_file = sys.argv[1]
    target_width = int(sys.argv[2])
    target_height = int(sys.argv[3])
    output_file = sys.argv[4] if len(sys.argv) > 4 else None
    
    print("=" * 60)
    print("🔧 PSD尺寸调整工具 V2 (二进制修改版)")
    print("=" * 60)
    
    resizer = PSDResizerV2(input_file, target_width, target_height, output_file)
    
    if resizer.resize_psd():
        print("=" * 60)
        print("✅ 调整完成!")
        print(f"📁 输出文件: {resizer.output_path}")
        print("=" * 60)
    else:
        print("=" * 60)
        print("❌ 调整失败!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()