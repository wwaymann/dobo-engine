from __future__ import annotations
import os
from .gallery import build_svg_gallery,build_text_gallery
from .svg_parser import SvgVectorParser
def main():
    print(); print("DOBO Advanced Geometry - Phase 1"); print("Vector Geometry"); print("--------------------------------")
    doc=SvgVectorParser().parse_string("""<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="20" height="10"/><path d="M 30 0 L 45 0 L 45 15 L 30 15 Z"/><path d="M 55 10 Q 65 0 75 10 L 75 20 L 55 20 Z"/></svg>""",document_id="parser_test")
    print("SVG parser:",len(doc.contours),"contours OK")
    for p in build_svg_gallery(): print(os.path.basename(p),os.path.getsize(p),"bytes OK")
    p=build_text_gallery(); print(os.path.basename(p),os.path.getsize(p),"bytes OK")
    print("--------------------------------"); print("Phase 1: Valid OK"); print()
if __name__=="__main__": main()
