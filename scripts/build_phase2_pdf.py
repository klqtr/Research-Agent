"""Render the phase-two report into a new PDF, preserving the original report."""
import os
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/"output/pdf/ResearchTrace_phase2_technical_report.pdf"
font=Path(os.environ["RESEARCHTRACE_REPORT_FONT"]) if os.getenv("RESEARCHTRACE_REPORT_FONT") else Path(os.environ.get("WINDIR","Windows"))/"Fonts"/"simsun.ttc"
if not font.exists():raise RuntimeError("请设置可用中文TrueType字体路径")
pdfmetrics.registerFont(TTFont("Phase2Body",str(font)))
INK=colors.HexColor("#183d33");MUTED=colors.HexColor("#607466");LINE=colors.HexColor("#d4decb")
body=ParagraphStyle("BodyCN",fontName="Phase2Body",fontSize=10.2,leading=17.5,textColor=INK,spaceAfter=8,wordWrap="CJK")
heading=ParagraphStyle("HeadingCN",parent=body,fontSize=18,leading=27,spaceAfter=18)
title=ParagraphStyle("TitleCN",parent=heading,fontSize=25,leading=36,spaceAfter=18)
small=ParagraphStyle("SmallCN",parent=body,fontSize=8.5,leading=14,textColor=MUTED)
story=[]


def paragraph(text,style=body):
    text=text.replace("`","").replace("**","").replace("\u2011","-").replace("\u2013","-").replace("\u2014","-")
    return Paragraph(escape(text),style)


def diagram(labels):
    drawing=Drawing(482,125);width=73;gap=8
    for i,label in enumerate(labels):
        x=i*(width+gap)
        drawing.add(Rect(x,65,width,40,rx=4,ry=4,fillColor=colors.HexColor("#edf1e3"),strokeColor=LINE))
        drawing.add(String(x+width/2,81,label,fontName="Phase2Body",fontSize=8.5,textAnchor="middle",fillColor=INK))
        if i<len(labels)-1:
            drawing.add(Line(x+width,85,x+width+gap,85,strokeColor=MUTED))
            drawing.add(Polygon([x+width+gap,85,x+width+gap-3,87,x+width+gap-3,83],fillColor=MUTED,strokeColor=MUTED))
    drawing.add(String(0,30,"只读白名单 / 同源恢复 / 共享累计预算 / 模式明确区分",fontName="Phase2Body",fontSize=9,fillColor=MUTED))
    return drawing


text=(ROOT/"reports/technical_report.md").read_text(encoding="utf-8")
paragraphs=text.split("\n\n")
section=0
for block in paragraphs:
    block=block.strip()
    if not block:continue
    if block.startswith("# "):
        story.append(paragraph("RESEARCHTRACE / PHASE 2",small));story.append(Spacer(1,18))
        story.append(paragraph("版本感知与证据约束的\n科研 Agent",title))
        story.append(paragraph("第二阶段技术报告研发稿",heading))
        story.append(paragraph("真实运行证据、模型待验收与未完成事项分别记录。",body))
        screen=ROOT/"reports/screenshots/phase2_evidence.jpg"
        if screen.exists():story.append(Image(str(screen),width=170*mm,height=95.7*mm))
        story.append(Spacer(1,12));story.append(paragraph("参赛者 / 学校 / 组别：待选手填写。\nAI辅助研发，未虚构人工标注或真实模型效果。",small))
    elif block.startswith("## "):
        section+=1;story.append(PageBreak());story.append(paragraph(block[3:],heading))
        if section==3:story.append(diagram(["Web / API","研究 Agent","工具与检索","授权模型","支持关卡","原页证据"]))
        if section==5:story.append(diagram(["结构化断言","来源ID/原文","版本一致性","五类支持度","一次修复","摘录/拒答"]))
    else:story.append(paragraph(block.replace("\n"," "),small if block.startswith("版本：") else body))


def decorate(canvas,document):
    canvas.saveState();canvas.setStrokeColor(LINE);canvas.line(20*mm,17*mm,190*mm,17*mm)
    canvas.setFont("Phase2Body",8);canvas.setFillColor(MUTED)
    canvas.drawString(20*mm,11*mm,"研证 ResearchTrace / 第二阶段研发稿")
    canvas.drawRightString(190*mm,11*mm,str(document.page));canvas.restoreState()


TARGET.parent.mkdir(parents=True,exist_ok=True)
document=SimpleDocTemplate(str(TARGET),pagesize=(210*mm,297*mm),leftMargin=20*mm,rightMargin=20*mm,topMargin=20*mm,bottomMargin=23*mm,
                           title="ResearchTrace 第二阶段技术报告",author="ResearchTrace AI-assisted development")
document.build(story,onFirstPage=decorate,onLaterPages=decorate)
print(str(TARGET))
