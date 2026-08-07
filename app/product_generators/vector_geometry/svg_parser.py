from __future__ import annotations
import math,re,xml.etree.ElementTree as ET
from .bezier import quadratic,cubic
from .contracts import VectorContour,VectorDocument
NUMBER=r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
TOKENIZER=re.compile(rf"([MmLlHhVvCcQqZzAa])|({NUMBER})")

class SvgVectorParser:
    def __init__(self,*,curve_segments:int=16,circle_segments:int=64)->None:
        self.curve_segments=curve_segments; self.circle_segments=circle_segments
    def parse_string(self,svg:str,*,document_id:str="svg")->VectorDocument:
        root=ET.fromstring(svg); contours=[]; n=0
        for e in root.iter():
            tag=e.tag.split("}",1)[-1].lower(); generated=()
            if tag=="rect": generated=(self._rect(e),)
            elif tag=="circle": generated=(self._circle(e),)
            elif tag=="ellipse": generated=(self._ellipse(e),)
            elif tag=="polygon":
                pts=self._points(e.attrib.get("points","")); generated=(pts,) if pts else ()
            elif tag=="path": generated=self._path(e.attrib.get("d",""))
            for pts in generated:
                if len(pts)>=3:
                    c=VectorContour(id=f"{document_id}:contour:{n}",points=pts,closed=True); c.validate(); contours.append(c); n+=1
        doc=VectorDocument(id=document_id,contours=tuple(contours),source="svg"); doc.validate(); return doc
    @staticmethod
    def _num(e,name,default=0.0):
        raw=e.attrib.get(name)
        if raw is None:return float(default)
        m=re.match(NUMBER,raw.strip())
        if not m: raise ValueError(f"SVG attribute {name} must be numeric.")
        return float(m.group(0))
    def _rect(self,e):
        x=self._num(e,"x"); y=self._num(e,"y"); w=self._num(e,"width"); h=self._num(e,"height")
        rx=max(self._num(e,"rx"),self._num(e,"ry"))
        if rx<=0:return ((x,y),(x+w,y),(x+w,y+h),(x,y+h))
        r=min(rx,w/2,h/2); out=[]
        for cx,cy,a0,a1 in ((x+w-r,y+r,-90,0),(x+w-r,y+h-r,0,90),(x+r,y+h-r,90,180),(x+r,y+r,180,270)):
            for i in range(8):
                a=math.radians(a0+(a1-a0)*i/7); out.append((cx+r*math.cos(a),cy+r*math.sin(a)))
        return tuple(out)
    def _circle(self,e):
        cx=self._num(e,"cx"); cy=self._num(e,"cy"); r=self._num(e,"r")
        return tuple((cx+r*math.cos(2*math.pi*i/self.circle_segments),cy+r*math.sin(2*math.pi*i/self.circle_segments)) for i in range(self.circle_segments))
    def _ellipse(self,e):
        cx=self._num(e,"cx"); cy=self._num(e,"cy"); rx=self._num(e,"rx"); ry=self._num(e,"ry")
        return tuple((cx+rx*math.cos(2*math.pi*i/self.circle_segments),cy+ry*math.sin(2*math.pi*i/self.circle_segments)) for i in range(self.circle_segments))
    @staticmethod
    def _points(raw):
        vals=[float(x) for x in re.findall(NUMBER,raw)]
        return tuple((vals[i],vals[i+1]) for i in range(0,len(vals)-1,2)) if len(vals)>=6 and len(vals)%2==0 else ()
    def _path(self,data):
        toks=[a or b for a,b in TOKENIZER.findall(data)]
        if any(t in {"A","a"} for t in toks): raise NotImplementedError("SVG A/a arcs are not supported in Phase 1.")
        paths=[]; pts=[]; i=0; cmd=None; current=(0.0,0.0); start=(0.0,0.0)
        def isc(t): return len(t)==1 and t.isalpha()
        def take(n):
            nonlocal i
            vals=[]
            for _ in range(n):
                if i>=len(toks) or isc(toks[i]): raise ValueError("Incomplete SVG path.")
                vals.append(float(toks[i])); i+=1
            return vals
        while i<len(toks):
            if isc(toks[i]): cmd=toks[i]; i+=1
            if cmd is None: raise ValueError("SVG path must start with command.")
            rel=cmd.islower(); up=cmd.upper()
            if up=="M":
                x,y=take(2); x=x+current[0] if rel else x; y=y+current[1] if rel else y
                pts=[(x,y)]; current=(x,y); start=current; cmd="l" if rel else "L"
            elif up=="L":
                x,y=take(2); x=x+current[0] if rel else x; y=y+current[1] if rel else y; current=(x,y); pts.append(current)
            elif up=="H":
                x,=take(1); x=x+current[0] if rel else x; current=(x,current[1]); pts.append(current)
            elif up=="V":
                y,=take(1); y=y+current[1] if rel else y; current=(current[0],y); pts.append(current)
            elif up=="Q":
                x1,y1,x2,y2=take(4); c=(current[0]+x1,current[1]+y1) if rel else (x1,y1); end=(current[0]+x2,current[1]+y2) if rel else (x2,y2); pts.extend(quadratic(current,c,end,segments=self.curve_segments)); current=end
            elif up=="C":
                x1,y1,x2,y2,x3,y3=take(6); c1=(current[0]+x1,current[1]+y1) if rel else (x1,y1); c2=(current[0]+x2,current[1]+y2) if rel else (x2,y2); end=(current[0]+x3,current[1]+y3) if rel else (x3,y3); pts.extend(cubic(current,c1,c2,end,segments=self.curve_segments)); current=end
            elif up=="Z":
                if len(pts)>=3: paths.append(tuple(pts))
                pts=[]; current=start; cmd=None
            else: raise NotImplementedError(f"SVG command {cmd} not supported.")
        return tuple(paths)
