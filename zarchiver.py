
import base64
from collections import defaultdict
import logging
from pathlib import Path
import typer
import zstandard

app = typer.Typer()

FILENAME_EXCLUSIONS = set([
   ".DS_Store"
])

@app.command()
def compress_file(file: Path):
   file_data = file.read_bytes()
   compressed_data = zstandard.compress(file_data, level=20)

   # Suffixing to keep the original filename.
   filename = file.suffix
   compressed_file = file.with_suffix(f"{filename}.zst")
   parent_name = compressed_file.parent.name

   # Output format.
   save_as = f"output/{parent_name}__{compressed_file.name}"
   save_as_file = Path(save_as)
   save_as_file.write_bytes(compressed_data)

   return len(compressed_data), len(file_data)

@app.command()
def compress_file_basket(basket: list[Path], name: str, prefix: str = ""):
   filenames = [file.name for file in basket if file.name not in FILENAME_EXCLUSIONS]
   datas: list[bytes] = []
   total_original = 0

   compressed_path_string = f"output/{(prefix+"____") if prefix != "" else ""}{name}.zst"
   filename_path_string = f"output/{(prefix+"____") if prefix != "" else ""}{name}.txt"
   filename_file = Path(filename_path_string)
   filename_file.write_text("\n".join(filenames))

   for path in basket:
      data = path.read_bytes()
      datas.append(data)
      total_original += len(data)

   combined_data = b"-----FILE_SEPARATOR-----".join(datas)
   compressed = zstandard.compress(combined_data, level=20)
   total_compressed = len(compressed)

   # Trying to reduce the size.
   compressed_file = Path(compressed_path_string)
   compressed_file.write_bytes(compressed)

   return total_compressed, total_original

def file_baskets(paths: list[Path], basket_size: int = 10):
   baskets: list[list[Path]] = []
   for i in range(0, len(paths), basket_size):
      baskets.append(paths[i:i+basket_size])
   return baskets

def parent_baskets(paths: list[Path]):
   baskets: dict[str, list[Path]] = defaultdict(list)
   for path in paths:
      baskets[path.parent.name].append(path)
   return list(baskets.values())

@app.command()
def compress_dir(path: Path, basket_size: int = 100):
   total_size = 0
   total_original_size = 0

   files: list[Path] = []
   for file in path.rglob("*"):
      if file.is_file():
         files.append(file)

   # Tested compressing iOS/Apple/Mac photos by baskets, and that resulted
   # in a better compression ratio. We're just looking for basics, because
   # the data size is so large.

   # Baskets are N-sized.
   # I am also going to try basketing based on the "memory name", as it might
   # reason that similar photos from the same day will compress better together,
   # and reduce noise from other files.

   # 100 saved per-file is approx: 
   # - #b1: 0.19MB per-file (PF)
   # - #b2: 0.21MB PF
   # - #b3: 0.19MB PF
   # - #b4: 0.06MB PF
   # This means for the above, we saved 65MB.

   # 25 saved per-file is approx:
   # - #b1: 0.16MB PF   
   # - #b2: 0.13MB PF
   # - #b3: 0.29 MB PF
   # - #b4: 0.04 ...
   # 0.05
   # 0.35
   # 0.30
   # 0.14
   # 0.09
   # 0.55
   # 0.10
   # 0.02
   # 0.05
   # 0.10
   # 0.03
   # 0.08
   # This means for the N=25, 16 baskets (4*N=100), we did a sum of: 2.48 * 400 = 248MB saved.

   # Based on this above experiment, we're able to get higher compression ratios at
   # N=25, than bringing it up to N=100. I'll now try N=10.

   for i, file_basket in enumerate(file_baskets(files, basket_size=basket_size)):
      size, original_size = compress_file_basket(file_basket, name=str(i), prefix="100basket")
      saved = original_size - size
      saved_per_file = saved / len(file_basket)
      total_size += size
      total_original_size += original_size

      logging.info(f"{total_original_size/(1024*1024):.2f}MB -> {total_size/(1024*1024):.2f}MB ({saved/(1024*1024):.2f}MB saved, {saved_per_file/(1024*1024):.2f}MB per file)")

if __name__ == "__main__":
   logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
   app()