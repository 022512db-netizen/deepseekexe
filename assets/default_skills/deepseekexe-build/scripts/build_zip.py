#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把便携版文件夹打成 UTF-8 文件名安全的 zip。

用法:
    python build_zip.py [源文件夹] [输出zip路径]

默认: 源=C:\\Users\\asus\\Desktop\\DeepSeekExe-portable
      输出=C:\\Users\\asus\\Desktop\\DeepSeekExe-portable.zip
"""

import os
import sys
import zipfile

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\asus\Desktop\DeepSeekExe-portable"
DST = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\asus\Desktop\DeepSeekExe-portable.zip"
ROOT_NAME = os.path.basename(SRC.rstrip("\\/"))


def main():
    if os.path.exists(DST):
        os.remove(DST)
    total = sum(len(fs) for _, _, fs in os.walk(SRC))
    done = 0
    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _dirs, files in os.walk(SRC):
            for fn in files:
                full = os.path.join(root, fn)
                arc = os.path.join(ROOT_NAME, os.path.relpath(full, SRC))
                z.write(full, arc)
                done += 1
                if done % 5000 == 0:
                    print("进度: %d/%d" % (done, total), flush=True)
    print("完成: %d 个文件, %.1f MB -> %s"
          % (done, os.path.getsize(DST) / 1024 / 1024, DST))


if __name__ == "__main__":
    sys.exit(main())
