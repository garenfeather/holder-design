import sys, os, glob, shutil
from PIL import Image
from psd_tools import PSDImage
from psd_tools.api.psd_image import PSDImage as PSDImageAPI
from psd_tools.api.layers import PixelLayer
from psd_tools.constants import Compression

def extract_layers_from_psd(psd_path) -> str:
    """
    Extracts specified layers ('part1', 'part2', 'part3', 'part4') from a PSD file
    and saves them as individual PNG files with the same dimensions as the PSD.

    Args:
        psd_path (str): The path to the input PSD file.
    """
    if not os.path.exists(psd_path):
        print(f"Error: File not found at {psd_path}")
        return None

    try:
        psd = PSDImage.open(psd_path)
        
        print(f"Opened PSD file: {psd_path}")
        print(f"PSD dimensions: {psd.width}x{psd.height}")
        if len(psd) == 0:
            print("No layers found. complete")
            return None

        # Create an output directory based on the PSD filename
        output_dir = os.path.splitext(os.path.basename(psd_path))[0] + "_layers"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for layer in psd:
            print(f"Found layer: '{layer.name}'")
            output_filename = os.path.join(output_dir, f"{layer.name}.png")
                
            # Manual composition to ensure canvas size is preserved.
            # This is the most robust method and avoids version-specific 'compose' issues.
                
            # 1. Get the layer's image data (cropped to its own bounding box).
            layer_image = layer.topil()
            if layer_image is None:
                print(f"Skipping layer '{layer.name}' because it has no pixel data.")
                continue

            # 2. Create a new transparent canvas with the full PSD dimensions.
            full_size_canvas = Image.new('RGBA', (psd.width, psd.height), (0, 0, 0, 0))
                
            # 3. Paste the layer's image onto the canvas at the correct offset.
            full_size_canvas.paste(layer_image, (layer.left, layer.top))
                
            # 4. Save the resulting canvas.
            full_size_canvas.save(output_filename)
            print(f"Saved '{layer.name}' to '{output_filename}'")

        print(f"\nExtraction complete. PNG files are in the '{output_dir}' directory.")
        return output_dir
    except Exception as e:
        print(f"An error occurred: {e}")
    return None

def resize_png_dir(input_dir: str, width: int, height: int) -> str:
    """将 input_dir 下所有 PNG 统一缩放为 (width, height)，输出到 output_dir。"""
    output_dir = input_dir + "_output"
    input_dir  = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 支持 .png / .PNG
    pngs = sorted(glob.glob(os.path.join(input_dir, "*.png")) +
                  glob.glob(os.path.join(input_dir, "*.PNG")))
    if not pngs:
        raise ValueError(f"No PNG files found in: {input_dir}")

    print(f"Found {len(pngs)} PNG(s). Target size: {width}x{height}")
    for i, src in enumerate(pngs, 1):
        name = os.path.basename(src)
        dst  = os.path.join(output_dir, name)

        im = Image.open(src)
        # 保留透明通道；非 RGBA 的也统一转成 RGBA
        if im.mode != "RGBA":
            im = im.convert("RGBA")

        # 直接缩放到目标尺寸（不保持比例）
        im_resized = im.resize((width, height), Image.LANCZOS)

        # 保存（尽量优化体积）
        im_resized.save(dst, optimize=True)
        print(f"[{i}/{len(pngs)}] {name} -> {width}x{height}")

    print(f"Done. Output dir: {output_dir}")
    return output_dir

def create_psd_from_dir(input_dir, output_psd):
    # 获取目录下所有 png
    png_files = sorted(glob.glob(os.path.join(input_dir, "*.png")))
    if not png_files:
        raise ValueError(f"No PNG files found in {input_dir}")

    base = Image.open(png_files[0]).convert("RGBA")
    w, h = base.size
    print(f"Creating PSD with dimensions: {w}x{h}")

    psd = PSDImageAPI.new(mode="RGBA", size=(w, h), color=(0, 0, 0, 0))

    for p in png_files:
        name = os.path.splitext(os.path.basename(p))[0]
        print(f"Adding layer: {name}")
        im = Image.open(p).convert("RGBA")

        if im.size != (w, h):
            canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            canvas.paste(im, (0, 0))
            im = canvas

        layer = PixelLayer.frompil(
            im,
            psd_file=psd,
            layer_name=name,
            top=0,
            left=0,
            compression=Compression.RLE,
        )
        psd.append(layer)

    # 输出到当前目录
    out_path = os.path.join(os.getcwd(), output_psd)
    psd.save(out_path)
    print(f"Saved: {out_path}")

def clear_temp_dir(path: str):
    """
    删除指定的临时目录及其中的所有文件/子目录。
    如果目录不存在，则忽略。
    """
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Removed temp dir: {path}")
    else:
        print(f"No such dir: {path} (skip)")

def full_scale_psd(psd_path: str, width: int, height: int) -> None:
    output_dir = extract_layers_from_psd(psd_path)
    resize_output_dir = resize_png_dir(output_dir, width, height)
    create_psd_from_dir(resize_output_dir, output_dir+"_output.psd")
    clear_temp_dir(output_dir)
    clear_temp_dir(resize_output_dir)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(1)

    input_path = sys.argv[1]
    width = int(sys.argv[2])
    height = int(sys.argv[3])
    try:
        full_scale_psd(input_path, width, height)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(2)